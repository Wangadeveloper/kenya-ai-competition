import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.sql_models import Post, User
from app.services.ai_service import AIService
from app.services.neo4j_service import Neo4jService
from app.services.notification_service import NotificationService

community_bp = Blueprint('community', __name__)

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
        if yt_url:
            try:
                ai = AIService()
                summary_text = ai.summarize_youtube_content(yt_url)
            except Exception:
                summary_text = f"Muhtasari wa video haupatikani kwa sasa. Kiungo: {yt_url}"

        full_body = content
        if yt_url:
            full_body += f"\n\n--- YouTube URL ---\n{yt_url}"
        if summary_text:
            full_body += f"\n\n--- AI Video Takeaways ---\n{summary_text}"

        # Determine post title based on user role
        if current_user.role == 'buyer':
            post_title = f"Quality Standard #{crop_tag}"
        else:
            post_title = f"Advisory regarding #{crop_tag}"

        new_post = Post(
            user_id=current_user.id,
            title=post_title,
            body=full_body
        )
        db.session.add(new_post)
        db.session.commit()
        
        # Traverses Graph relationships to broadcast across network nodes
        try:
            ns = Neo4jService()
            ns.sync_post_node(new_post.id, new_post.title, current_user.phone_number)
            with ns.driver.session() as session:
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
            ns.close()
        except Exception:
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
        ns = Neo4jService()
        ns.create_subscription_relationship(
            subscriber_phone=current_user.phone_number,
            subscriber_name=current_user.full_name,
            farmer_phone=farmer_phone,
            channel=channel
        )
        ns.close()
        flash(f"Utafahamishwa updates kutoka kwa mkulima huyu kupitia {channel}!", "success")
    except Exception:
        flash("Graph database network serialization fallback encountered.", "danger")
        
    return redirect(url_for('community.feed'))


@community_bp.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def comment(post_id):
    body = request.form.get('body', '').strip()
    if not body:
        flash('Comment content cannot be empty.', 'danger')
        return redirect(url_for('community.feed'))

    post = Post.query.get_or_404(post_id)
    from app.models.sql_models import Comment
    new_comment = Comment(
        user_id=current_user.id,
        post_id=post.id,
        body=body
    )
    db.session.add(new_comment)
    db.session.commit()

    # Sync comment to Neo4j
    try:
        ns = Neo4jService()
        ns.sync_comment_node(new_comment.id, body, post.id, current_user.phone_number)
        ns.close()
    except Exception as e:
        print("Neo4j comment sync error:", e)

    flash('Comment shared successfully!', 'success')
    return redirect(url_for('community.feed'))