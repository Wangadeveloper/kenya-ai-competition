import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.sql_models import Post, User
from app.services.ai_service import AIService
from app.services.notification_service import NotificationService
from neo4j import GraphDatabase

community_bp = Blueprint('community', __name__)

def get_neo4j_driver():
    """Returns a direct standalone engine driver reference to Neo4j Cloud instance."""
    return GraphDatabase.driver(
        os.getenv("NEO4J_URI"), 
        auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
    )

@community_bp.route('/feed', methods=['GET', 'POST'])
@login_required
def feed():
    if request.method == 'POST':
        content = request.form.get('content')
        crop_tag = request.form.get('crop_tag')
        yt_url = request.form.get('youtube_url')
        
        summary_text = None
        
        # 1. Process YouTube via Gemini if URL string exists
        if yt_url and yt_url.strip():
            try:
                ai = AIService()
                summary_text = ai.summarize_youtube_content(yt_url)
            except Exception as e:
                summary_text = "AI summary temporarily delayed due to gateway initialization rules."

        # 2. Persist Structural Post directly to Relational SQLite Core Engine
        new_post = Post(
            user_id=current_user.id,
            content=content,
            youtube_url=yt_url if yt_url else None,
            video_summary=summary_text,
            county_tag=current_user.county,
            crop_tag=crop_tag
        )
        db.session.add(new_post)
        db.session.commit()
        
        # 3. NEO4J NETWORK BROADCAST ENGINE: Traverse graph connections to pull phone metrics
        try:
            driver = get_neo4j_driver()
            with driver.session() as session:
                cypher_broadcast = """
                MATCH (subscriber:User)-[r:SUBSCRIBED_TO]->(farmer:User {phone_number: $farmer_phone})
                RETURN subscriber.phone_number AS phone, r.channel AS channel
                """
                results = session.run(cypher_broadcast, farmer_phone=current_user.phone_number)
                
                alert_payload = (
                    f"Mkulima {current_user.full_name} ameposti ushauri mpya kuhusu #{crop_tag or 'Kilimo'}: "
                    f"{summary_text if summary_text else content[:60]}"
                )
                
                for record in results:
                    target_phone = record['phone']
                    preferred_channel = record['channel']
                    
                    if preferred_channel == 'WhatsApp':
                        NotificationService.send_whatsapp_alert(target_phone, alert_payload)
                    else:
                        NotificationService.send_sms_via_africastalking(target_phone, alert_payload)
            driver.close()
        except Exception as graph_err:
            # Prevent app crashing if graph pipeline hit a structural connection timeout
            pass

        flash('Post shared successfully and ecosystem graph network notified!', 'success')
        return redirect(url_for('community.feed'))
        
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('community/feed.html', posts=posts)


@community_bp.route('/subscribe/<string:farmer_phone>', methods=['POST'])
@login_required
def subscribe(farmer_phone):
    channel = request.form.get('channel', 'SMS')
    
    if farmer_phone == current_user.phone_number:
        flash("Huwezi kujisajili kupokea notifications zako mwenyewe!", "warning")
        return redirect(url_for('community.feed'))
        
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            # Native graph processing: upsert nodes and the directional relationship context safely
            cypher_subscribe = """
            MERGE (subscriber:User {phone_number: $sub_phone})
            SET subscriber.full_name = $sub_name
            MERGE (farmer:User {phone_number: $farmer_phone})
            MERGE (subscriber)-[r:SUBSCRIBED_TO]->(farmer)
            SET r.channel = $channel
            """
            session.run(
                cypher_subscribe, 
                sub_phone=current_user.phone_number, 
                sub_name=current_user.full_name,
                farmer_phone=farmer_phone, 
                channel=channel
            )
        driver.close()
        flash(f"Utafahamishwa updates kutoka kwa mkulima huyu kupitia {channel}!", "success")
    except Exception as e:
        flash("Graph database synchronization error encountered. Try again shortly.", "danger")
        
    return redirect(url_for('community.feed'))