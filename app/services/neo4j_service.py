from neo4j import GraphDatabase
from flask import current_app
from datetime import datetime

class Neo4jService:
    def __init__(self):
        config = current_app.config
        self.driver = GraphDatabase.driver(
            config['NEO4J_URI'], 
            auth=(config['NEO4J_USER'], config['NEO4J_PASSWORD'])
        )

    def close(self):
        self.driver.close()

    def sync_user_node(self, user_data):
        """
        Maintains structural integrity for Farmer or Officer profiles.
        Maps localized context edges to sub-counties, crops, and SACCO nodes.
        """
        with self.driver.session() as session:
            query = """
            MERGE (u:User {phone_number: $phone_number})
            SET u.user_id = $user_id,
                u.full_name = $full_name,
                u.role = $role,
                u.age = $age,
                u.gender = $gender,
                u.credit_score = $credit_score,
                u.farm_size_acres = $farm_size,
                u.water_source = $water_source,
                u.national_id = $national_id,
                u.ward = $ward,
                u.soil_type = $soil_type,
                u.irrigation_type = $irrigation_type,
                u.livestock_count = $livestock_count,
                u.years_farming = $years_farming,
                u.smartphone_owned = $smartphone_owned,
                u.literacy_level = $literacy_level,
                u.preferred_language = $preferred_language,
                u.updated_at = datetime()

            // Map Geographic Context
            MERGE (loc:Location {sub_county: $sub_county, county: $county})
            MERGE (u)-[:LOCATED_IN]->(loc)

            WITH u
            // Conditionally process Primary Crop node mapping
            UNWIND case when $primary_crop IS NOT NULL AND $primary_crop <> '' then [$primary_crop] else [] end as cropName
            MERGE (c:Crop {name: cropName})
            MERGE (u)-[:GROWS]->(c)

            WITH u
            // Conditionally process SACCO network mapping
            UNWIND case when $sacco_name IS NOT NULL AND $sacco_name <> '' then [$sacco_name] else [] end as saccoName
            MERGE (s:SACCO {name: saccoName})
            MERGE (u)-[:MEMBER_OF]->(s)
            """
            session.run(
                query,
                user_id=user_data.get('id'),
                phone_number=user_data.get('phone_number'),
                full_name=user_data.get('full_name'),
                role=user_data.get('role'),
                age=user_data.get('age'),
                gender=user_data.get('gender'),
                credit_score=user_data.get('credit_score', 700),
                farm_size=user_data.get('farm_size', 0.0),
                water_source=user_data.get('water_source', 'Rain-fed'),
                county=user_data.get('county'),
                sub_county=user_data.get('sub_county'),
                primary_crop=user_data.get('primary_crop'),
                sacco_name=user_data.get('sacco_name'),
                national_id=user_data.get('national_id'),
                ward=user_data.get('ward'),
                soil_type=user_data.get('soil_type', 'Clay loam'),
                irrigation_type=user_data.get('irrigation_type', 'Rain-fed'),
                livestock_count=user_data.get('livestock_count', 0),
                years_farming=user_data.get('years_farming', 0),
                smartphone_owned=user_data.get('smartphone_owned', True),
                literacy_level=user_data.get('literacy_level', 'Basic'),
                preferred_language=user_data.get('preferred_language', 'English')
            )


    def log_field_visit(self, officer_phone, farmer_phone, visit_id, condition, notes, action, coordinates):
        """
        Injects a temporal transaction link between a Field Officer and a Farmer.
        """
        with self.driver.session() as session:
            query = """
            MATCH (officer:User {phone_number: $officer_phone, role: 'officer'})
            MATCH (farmer:User {phone_number: $farmer_phone, role: 'farmer'})
            
            CREATE (officer)-[v:VISITED_BY {
                visit_id: $visit_id,
                date: datetime(),
                crop_health: $condition,
                gps_location: $coordinates,
                recommended_action: $action
            }]->(farmer)
            
            // Link current health status contextual patterns to the farmer node properties
            SET farmer.last_crop_condition = $condition,
                farmer.last_visit_date = datetime()
            
            RETURN id(v)
            """
            session.run(
                query,
                officer_phone=officer_phone,
                farmer_phone=farmer_phone,
                visit_id=visit_id,
                condition=condition,
                notes=notes,
                action=action,
                coordinates=coordinates
            )

    def track_loan_issuance(self, farmer_phone, loan_id, amount, purpose, status):
        """
        Establishes risk management edges. Connects loan requests over temporal bounds.
        """
        with self.driver.session() as session:
            query = """
            MATCH (farmer:User {phone_number: $farmer_phone, role: 'farmer'})
            MERGE (l:Loan {loan_id: $loan_id})
            SET l.amount = $amount,
                l.purpose = $purpose,
                l.current_status = $status,
                l.created_at = datetime()
                
            MERGE (farmer)-[r:APPLIED_FOR]->(l)
            SET r.timestamp = datetime()
            """
            session.run(query, farmer_phone=farmer_phone, loan_id=loan_id, amount=amount, purpose=purpose, status=status)

    def update_market_node(self, crop_name, market_location, price, trend):
        """
        Maintains supply chain telemetry nodes for competitive open-market mapping.
        """
        with self.driver.session() as session:
            query = """
            MERGE (c:Crop {name: $crop_name})
            MERGE (m:Market {name: $market_location})
            
            MERGE (m)-[p:SELLS_CROP]->(c)
            SET p.price_per_kg = $price,
                p.trend = $trend,
                p.last_updated = datetime()
            """
            session.run(query, crop_name=crop_name, market_location=market_location, price=price, trend=trend)

    def search_graph_rag_context(self, farmer_phone):
        """
        Multi-hop context extraction. Builds the structured profile used by 
        Gemini AI to generate highly localized agronomy and financial solutions.
        """
        with self.driver.session() as session:
            query = """
            MATCH (f:User {phone_number: $farmer_phone, role: 'farmer'})-[:LOCATED_IN]->(loc:Location)
            MATCH (f)-[:GROWS]->(c:Crop)
            
            OPTIONAL MATCH (f)-[v:VISITED_BY]-(officer:User)
            OPTIONAL MATCH (f)-[:MEMBER_OF]->(sacco:SACCO)
            OPTIONAL MATCH (market:Market)-[p:SELLS_CROP]->(c) WHERE market.name CONTAINS loc.county
            
            RETURN f.full_name AS farmer_name,
                   f.credit_score AS credit_score,
                   loc.county AS county,
                   loc.sub_county AS sub_county,
                   c.name AS crop,
                   f.last_crop_condition AS last_condition,
                   sacco.name AS sacco_name,
                   market.name AS local_market,
                   p.price_per_kg AS market_price
            LIMIT 1
            """
            result = session.run(query, farmer_phone=farmer_phone)
            record = result.single()
            return record.data() if record else None

    def get_regional_outbreak_risk(self, county, crop_name):
        """
        Analyzes field visit history from nearby farms to detect pest or disease trends.
        """
        with self.driver.session() as session:
            query = """
            MATCH (loc:Location {county: $county})<-[:LOCATED_IN]-(other:User {role: 'farmer'})
            MATCH (other)-[:GROWS]->(c:Crop {name: $crop_name})
            MATCH (officer:User {role: 'officer'})-[v:VISITED_BY]->(other)
            WHERE v.crop_health IN ['Pest Outbreak', 'Nutrient Deficient']
              AND duration.inDays(v.date, datetime()).days <= 14
            RETURN count(v) AS active_alerts
            """
            result = session.run(query, county=county, crop_name=crop_name)
            return result.single().get("active_alerts", 0)

    def get_similar_farmers(self, county, crop_name, phone_number):
        """
        Retrieves other farmers in the same county cultivating the same crop.
        """
        with self.driver.session() as session:
            query = """
            MATCH (other:User)-[:LOCATED_IN]->(loc:Location)
            WHERE loc.county = $county AND other.phone_number <> $phone_number
              AND other.role = 'farmer'
            MATCH (other)-[:GROWS]->(c:Crop {name: $crop_name})
            RETURN other.full_name AS name
            """
            result = session.run(query, county=county, crop_name=crop_name, phone_number=phone_number)
            return [{"name": record["name"]} for record in result]

    def create_subscription_relationship(self, subscriber_phone, subscriber_name, farmer_phone, channel):
        """
        Establishes a directional SUBSCRIBED_TO graph relationship.
        """
        with self.driver.session() as session:
            query = """
            MATCH (subscriber:User {phone_number: $subscriber_phone})
            MATCH (farmer:User {phone_number: $farmer_phone})
            MERGE (subscriber)-[r:SUBSCRIBED_TO]->(farmer)
            SET r.channel = $channel,
                r.updated_at = datetime()
            """
            session.run(
                query,
                subscriber_phone=subscriber_phone,
                farmer_phone=farmer_phone,
                channel=channel
            )

    def sync_post_node(self, post_id, title, author_phone):
        """
        Syncs a Post node and links the author User node to it via :POSTED.
        """
        with self.driver.session() as session:
            query = """
            MATCH (u:User {phone_number: $author_phone})
            MERGE (p:Post {post_id: $post_id})
            SET p.title = $title, p.updated_at = datetime()
            MERGE (u)-[:POSTED]->(p)
            """
            session.run(query, post_id=post_id, title=title, author_phone=author_phone)

    def sync_comment_node(self, comment_id, body, post_id, commenter_phone):
        """
        Syncs a Comment node and links commenter to it via :COMMENTED, and comment to Post via :ON_POST.
        """
        with self.driver.session() as session:
            query = """
            MATCH (u:User {phone_number: $commenter_phone})
            MATCH (p:Post {post_id: $post_id})
            MERGE (c:Comment {comment_id: $comment_id})
            SET c.body = $body, c.updated_at = datetime()
            MERGE (u)-[:COMMENTED]->(c)
            MERGE (c)-[:ON_POST]->(p)
            """
            session.run(query, comment_id=comment_id, body=body, post_id=post_id, commenter_phone=commenter_phone)

    def log_pest_disease_outbreak(self, farmer_phone, name, type, severity):
        """
        Merges Pest or Disease node and connects the farmer to it via :AFFECTED_BY.
        """
        with self.driver.session() as session:
            # Type must be 'Pest' or 'Disease'
            label = "Pest" if type.lower() == "pest" else "Disease"
            query = f"""
            MATCH (f:User {{phone_number: $farmer_phone, role: 'farmer'}})
            MERGE (n:{label} {{name: $name}})
            MERGE (f)-[r:AFFECTED_BY]->(n)
            SET r.severity = $severity, r.date = datetime()
            """
            session.run(query, farmer_phone=farmer_phone, name=name, severity=severity)

    def track_repayment(self, farmer_phone, loan_id, repayment_id, amount, status):
        """
        Merges Repayment node and links User to it via :REPAID, and Repayment to Loan via :FOR_LOAN.
        """
        with self.driver.session() as session:
            query = """
            MATCH (f:User {phone_number: $farmer_phone, role: 'farmer'})
            MATCH (l:Loan {loan_id: $loan_id})
            MERGE (r:Repayment {repayment_id: $repayment_id})
            SET r.amount = $amount, r.status = $status, r.created_at = datetime()
            MERGE (f)-[:REPAID]->(r)
            MERGE (r)-[:FOR_LOAN]->(l)
            """
            session.run(query, farmer_phone=farmer_phone, loan_id=loan_id, repayment_id=repayment_id, amount=amount, status=status)


    def log_input_purchase(self, farmer_phone, input_name, manufacturer, batch, compliance_status):
        """
        EU Compliance Graph Module: Merges an Input node and links the farmer via :PURCHASED_INPUT.
        compliance_status: 'Safe', 'Flagged', or 'Unverified'
        This edge is queryable by peers in the same county/crop cluster for GraphRAG risk propagation.
        """
        with self.driver.session() as session:
            query = """
            MATCH (f:User {phone_number: $farmer_phone, role: 'farmer'})
            MERGE (i:Input {name: $input_name, batch: $batch})
            SET i.manufacturer = $manufacturer,
                i.last_updated = datetime()
            MERGE (f)-[r:PURCHASED_INPUT]->(i)
            SET r.compliance_status = $compliance_status,
                r.recorded_at = datetime()
            """
            session.run(
                query,
                farmer_phone=farmer_phone,
                input_name=input_name,
                manufacturer=manufacturer,
                batch=batch,
                compliance_status=compliance_status
            )


    def link_crop_to_market(self, crop_name, market_name):
        """
        EU Compliance Graph Module: Creates a DESTINED_FOR edge between a Crop and a Market node.
        Used to signal export intent (e.g. Maize -> EU) for advisory and loan risk context.
        """
        with self.driver.session() as session:
            query = """
            MERGE (c:Crop {name: $crop_name})
            MERGE (m:Market {name: $market_name})
            MERGE (c)-[r:DESTINED_FOR]->(m)
            SET r.updated_at = datetime()
            """
            session.run(query, crop_name=crop_name, market_name=market_name)


    def get_compliance_exposed_peers(self, county, crop_name, farmer_phone):
        """
        EU Compliance GraphRAG Query: Finds peer farmers in the same county growing the same crop
        who have purchased inputs flagged as non-EU-compliant.
        Used to proactively broadcast alerts to at-risk cluster members.
        Returns a list of dicts: [{name, phone_number, input_name}]
        """
        with self.driver.session() as session:
            query = """
            MATCH (other:User)-[:LOCATED_IN]->(loc:Location)
            WHERE loc.county = $county AND other.phone_number <> $farmer_phone
              AND other.role = 'farmer'
            MATCH (other)-[:GROWS]->(c:Crop {name: $crop_name})
            MATCH (other)-[r:PURCHASED_INPUT]->(i:Input)
            WHERE r.compliance_status = 'Flagged'
            RETURN other.full_name AS name,
                   other.phone_number AS phone_number,
                   i.name AS input_name
            """
            result = session.run(query, county=county, crop_name=crop_name, farmer_phone=farmer_phone)
            return [dict(record) for record in result]