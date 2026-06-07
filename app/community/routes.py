import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.sql_models import Post, User
from app.services.ai_service import AIService
from app.services.notification_service import NotificationService
from neo4j import GraphDatabase

community_bp = Blueprint('community', __name__)

def get_neo4j_driver():
    """Returns a direct standalone engine driver reference using active Flask context settings."""
    return GraphDatabase.driver(
        current_app.config.get("NEO4J_URI", os.getenv("NEO4J_URI")), 
        auth=(
            current_app.config.get("NEO4J_USER", os.getenv("NEO4J_USERNAME")), 
            current_app.config.get("NEO4J_PASSWORD", os.getenv("NEO4J_PASSWORD"))
        )
    )

@community_bp.route('/feed', methods=['GET', 'POST'])
@login_required
def feed():
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        crop_tag = request.form.get('crop_tag', 'General')
        yt_url = request.form.get('youtube_url', '').strip()
        
        if not content:
            flash('Post body content cannot be empty.', 'danger')
            return redirect(url_for('community.feed'))

        summary_text = None
        
        # 1. Process YouTube URL link via Gemini using existing summary service pipelines
        if yt_url:
            try:
                ai = AIService()
                summary_text = ai.summarize_youtube_content(yt_url)
            except Exception as e:
                summary_text = f"Muhtasari wa video haupatikani kwa sasa. Kiungo: {yt_url}"

        # Combine summary data directly into the standard Post schema parameters
        full_body = content
        if summary_text:
            full_body += f"\n\n--- AI Video Takeaways ---\n{summary_text}"

        # 2. Persist directly into the Relational Core SQLite Database Structure
        new_post = Post(
            user_id=current_user.id,
            title=f"Advisory regarding #{crop_tag}",
            body=full_body
        )
        db.session.add(new_post)
        db.session.commit()
        
        # 3. NEO4J NETWORK BROADCAST ENGINE: Traverse graph network connections to notify peers
        try:
            driver = get_neo4j_driver()
            with driver.session() as session:
                cypher_broadcast = """
                MATCH (subscriber:User)-[r:SUBSCRIBED_TO]->(farmer:User {phone_number: $farmer_phone})
                RETURN subscriber.phone_number AS phone, r.channel AS channel
                """
                results = session.run(cypher_broadcast, farmer_phone=current_user.phone_number)
                
                alert_payload = (
                    f"Mkulima {current_user.full_name} ameposti ushauri mpya kuhusu #{crop_tag}: "
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
            # Safe boundary fall-through to prevent thread crashing due to offline graph timeouts
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
        flash("Graph database network serialization fallback encountered.", "danger")
        
    return redirect(url_for('community.feed'))