import os
from app import create_app
from app.extensions import db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Auto-initialize and migrate lightweight operational tables locally inside development targets
        db.create_all()
    
    # Executed configurations matching typical resource-constrained proxy pipelines
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)