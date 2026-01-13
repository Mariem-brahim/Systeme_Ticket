import os
from pathlib import Path
from app import create_app

app = create_app()
if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

    base_dir = Path(__file__).parent
    cert_file = base_dir / 'cert.pem'
    key_file = base_dir / 'key.pem'
    ssl_context = (str(cert_file), str(key_file)) if cert_file.exists() and key_file.exists() else None

    app.run(debug=debug, host='0.0.0.0', port=5000, ssl_context=ssl_context)