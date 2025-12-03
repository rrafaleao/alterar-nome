from flask import Blueprint, render_template, jsonify
from config.database import db

main = Blueprint("main", __name__, url_prefix="/")

@main.get("/")
def index():
    return render_template('main.html')

@main.get("/test-db")
def test_db():
    """Rota para testar a conexão com o banco de dados"""
    try:
        # Tenta executar uma query simples
        result = db.session.execute(db.text("SELECT 1"))
        db.session.close()
        return jsonify({
            "status": "success",
            "message": "Conexão com o banco de dados estabelecida com sucesso!",
            "database": "Banco de dados funcionando corretamente"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Erro ao conectar ao banco de dados",
            "error": str(e)
        }), 500