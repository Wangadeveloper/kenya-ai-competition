import os
from app import create_app
from app.extensions import db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Auto-initialize and migrate lightweight operational tables locally inside development targets
        db.create_all()
        
        # Seed data
        from app.models.sql_models import User, Sacco, ExtensionGuide, MarketInsight
        if Sacco.query.count() == 0:
            s1 = Sacco(name="Kakamega Cooperative SACCO", county="Kakamega")
            s2 = Sacco(name="Bungoma Cooperative SACCO", county="Bungoma")
            db.session.add_all([s1, s2])
            db.session.commit()

        if User.query.count() == 0:
            # Seed default officer
            officer = User(
                username="officer",
                email="officer@agrinexus.co.ke",
                full_name="Officer Jane",
                phone_number="+254712345678",
                role="officer",
                assigned_region="Kakamega - Lurambi",
                county="Kakamega",
                sub_county="Lurambi",
                age=35,
                gender="Female",
                employee_id="OFF-001"
            )
            officer.set_password("password")
            
            # Seed farmers
            sacco1 = Sacco.query.filter_by(name="Kakamega Cooperative SACCO").first()
            sacco2 = Sacco.query.filter_by(name="Bungoma Cooperative SACCO").first()
            
            f1 = User(
                username="farmer1",
                email="farmer1@agrinexus.co.ke",
                full_name="Farmer John",
                phone_number="+254711111111",
                role="farmer",
                county="Kakamega",
                sub_county="Lurambi",
                age=42,
                gender="Male",
                primary_crop="Maize",
                water_source="Rain-fed",
                farm_size=2.5,
                credit_score=720,
                sacco_id=sacco1.id if sacco1 else None,
                smartphone_owned=True,
                soil_type="Clay loam",
                irrigation_type="Rain-fed",
                years_farming=10,
                preferred_language="Swahili",
                literacy_level="Basic",
                ward="Lurambi Ward",
                national_id="12345678"
            )
            f1.set_password("password")
            
            f2 = User(
                username="farmer2",
                email="farmer2@agrinexus.co.ke",
                full_name="Farmer Mary",
                phone_number="+254722222222",
                role="farmer",
                county="Bungoma",
                sub_county="Kimilili",
                age=38,
                gender="Female",
                primary_crop="Beans",
                water_source="Borehole",
                farm_size=1.5,
                credit_score=680,
                sacco_id=sacco2.id if sacco2 else None,
                smartphone_owned=False,
                soil_type="Sandy loam",
                irrigation_type="Borehole Pumping",
                years_farming=5,
                preferred_language="English",
                literacy_level="Fluent",
                ward="Kimilili Ward",
                national_id="87654321"
            )
            f2.set_password("password")
            
            db.session.add_all([officer, f1, f2])
            db.session.commit()

            # Seed Farm Ledger entries for farmers
            from app.models.sql_models import FarmLedger, CropYield
            
            # Farmer John (f1) ledger and yield
            l1 = FarmLedger(user_id=f1.id, record_type='income', category='Harvest Sale', amount=150000.0, description='Sold 45 bags of premium White Maize to Kakamega Market', compliance_status='Safe')
            l2 = FarmLedger(user_id=f1.id, record_type='expense', category='Fertilizer', amount=35000.0, description='Bought certified organic bio-fertilizer DAP alternatives', compliance_status='Safe')
            l3 = FarmLedger(user_id=f1.id, record_type='expense', category='Seeds', amount=12000.0, description='Bought 25kg Pioneer Hybrid Maize Seeds', compliance_status='Safe')
            y1 = CropYield(user_id=f1.id, crop_name='Maize', season_name='Long Rains 2025', acreage=2.5, yield_kg=3200.0, revenue=120000.0)
            
            # Farmer Mary (f2) ledger and yield
            l4 = FarmLedger(user_id=f2.id, record_type='income', category='Harvest Sale', amount=95000.0, description='Sold yellow beans locally', compliance_status='Safe')
            l5 = FarmLedger(user_id=f2.id, record_type='expense', category='Pesticide', amount=25000.0, description='Bought generic pesticide containing high cadmium limits', compliance_status='Flagged')
            l6 = FarmLedger(user_id=f2.id, record_type='expense', category='Seeds', amount=8000.0, description='Bought local bush bean seeds', compliance_status='Safe')
            y2 = CropYield(user_id=f2.id, crop_name='Beans', season_name='Long Rains 2025', acreage=1.5, yield_kg=1200.0, revenue=85000.0)

            db.session.add_all([l1, l2, l3, y1, l4, l5, l6, y2])
            db.session.commit()

            # Sync to Neo4j
            try:
                from app.services.neo4j_service import Neo4jService
                ns = Neo4jService()
                for u in [officer, f1, f2]:
                    user_payload = {
                        'id': u.id,
                        'phone_number': u.phone_number,
                        'full_name': u.full_name,
                        'role': u.role,
                        'age': u.age,
                        'gender': u.gender,
                        'credit_score': getattr(u, 'credit_score', 700),
                        'farm_size': getattr(u, 'farm_size', 0.0),
                        'water_source': getattr(u, 'water_source', 'Rain-fed'),
                        'county': u.county,
                        'sub_county': u.sub_county,
                        'primary_crop': getattr(u, 'primary_crop', None),
                        'sacco_name': u.sacco.name if u.sacco else None,
                        'national_id': getattr(u, 'national_id', None),
                        'ward': getattr(u, 'ward', None),
                        'soil_type': getattr(u, 'soil_type', None),
                        'irrigation_type': getattr(u, 'irrigation_type', None),
                        'livestock_count': getattr(u, 'livestock_count', 0),
                        'years_farming': getattr(u, 'years_farming', 0),
                        'smartphone_owned': getattr(u, 'smartphone_owned', True),
                        'literacy_level': getattr(u, 'literacy_level', None),
                        'preferred_language': getattr(u, 'preferred_language', None)
                    }
                    ns.sync_user_node(user_payload)
                ns.close()
            except Exception as e:
                print("Neo4j seeding error:", e)

        if MarketInsight.query.count() == 0:
            m1 = MarketInsight(crop_name="Maize (White)", market_location="Kakamega Open Market", current_price_per_kg=38.0, price_trend="Stable")
            m2 = MarketInsight(crop_name="Beans (Yellow)", market_location="Chwele Market", current_price_per_kg=138.0, price_trend="Rising")
            m3 = MarketInsight(crop_name="Potatoes (Irish)", market_location="Kimilili Market", current_price_per_kg=45.0, price_trend="Falling")
            db.session.add_all([m1, m2, m3])
            db.session.commit()

        if ExtensionGuide.query.count() == 0:
            # Seed guides
            guides = [
                {
                    "title": "Maize Cultivation Guide",
                    "content": "Maize grows best in well-drained, fertile loam soils with a pH of 5.5 to 7.0. Plant seeds 2-3 cm deep, with a spacing of 75cm between rows and 25cm between plants. Apply DAP fertilizer at planting and top-dress with CAN when the maize is knee-high (about 3-4 weeks). Watch out for Fall Armyworm and use appropriate pest controls."
                },
                {
                    "title": "Beans Production Manual",
                    "content": "Beans require moderate rainfall and well-drained soils. Spacing should be 45cm between rows and 15cm between plants. Use phosphorus-rich fertilizers at planting. Control aphids, bean fly, and anthracnose using early-season spraying and crop rotation."
                },
                {
                    "title": "Irish Potato Management",
                    "content": "Potatoes thrive in cool areas with fertile, loose soils. Plant tubers in ridges spaced 75cm apart and 30cm between plants. Early blight and late blight are major disease threats; apply fungicides before heavy rains. Harvest when the vines turn yellow and dry."
                }
            ]
            from app.services.ai_service import AIService
            ai = AIService()
            for g in guides:
                emb = None
                try:
                    emb = ai.generate_embedding(g["content"])
                except Exception as e:
                    print(f"Error generating embedding for {g['title']}: {e}")
                guide = ExtensionGuide(title=g["title"], content=g["content"], embedding=emb)
                db.session.add(guide)
            db.session.commit()
    
    # Executed configurations matching typical resource-constrained proxy pipelines
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)