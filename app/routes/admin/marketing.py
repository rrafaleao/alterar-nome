from flask import render_template, request, jsonify, session
from datetime import datetime
from config.database import db
from . import admin
from .decorators import login_required, store_required
from app.models import Promotion, PromotionProduct, PromotionCategory, Product, Category


@admin.route('/promotions')
@login_required
@store_required
def promotions_page():
    """Página de promoções"""
    store_id = session.get('store_id')
    
    # Buscar todas as promoções da loja
    promotions = Promotion.query.filter_by(store_id=store_id).order_by(Promotion.created_at.desc()).all()
    
    # Contar por status
    now = datetime.utcnow()
    active_count = sum(1 for p in promotions if p.status == 'active')
    scheduled_count = sum(1 for p in promotions if p.status == 'scheduled')
    expired_count = sum(1 for p in promotions if p.status == 'expired')
    
    # Buscar produtos e categorias para o modal
    products = Product.query.filter_by(store_id=store_id, active=True).order_by(Product.title).all()
    categories = Category.query.filter_by(store_id=store_id).order_by(Category.name).all()
    
    return render_template(
        'admin/promotions.html',
        promotions=promotions,
        products=products,
        categories=categories,
        total_count=len(promotions),
        active_count=active_count,
        scheduled_count=scheduled_count,
        expired_count=expired_count
    )


@admin.route('/promotions/create', methods=['POST'])
@login_required
@store_required
def create_promotion():
    """Criar nova promoção"""
    try:
        data = request.get_json()
        store_id = session.get('store_id')
        
        # Validar campos obrigatórios
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'Nome da promoção é obrigatório'}), 400
        
        if not data.get('discount_value'):
            return jsonify({'success': False, 'error': 'Valor do desconto é obrigatório'}), 400
        
        if not data.get('start_date') or not data.get('end_date'):
            return jsonify({'success': False, 'error': 'Datas de início e fim são obrigatórias'}), 400
        
        # Criar promoção
        promotion = Promotion(
            store_id=store_id,
            name=data['name'],
            description=data.get('description', ''),
            discount_type=data.get('discount_type', 'percentage'),
            discount_value=float(data['discount_value']),
            min_purchase_amount=float(data.get('min_purchase_amount', 0)),
            max_discount_amount=float(data['max_discount_amount']) if data.get('max_discount_amount') else None,
            start_date=datetime.fromisoformat(data['start_date'].replace('Z', '+00:00').replace('+00:00', '')),
            end_date=datetime.fromisoformat(data['end_date'].replace('Z', '+00:00').replace('+00:00', '')),
            is_active=data.get('is_active', True),
            applies_to=data.get('applies_to', 'all')
        )
        
        db.session.add(promotion)
        db.session.flush()  # Get the promotion ID
        
        # Adicionar produtos específicos se aplicável
        if data.get('applies_to') == 'products' and data.get('product_ids'):
            for product_id in data['product_ids']:
                pp = PromotionProduct(promotion_id=promotion.id, product_id=product_id)
                db.session.add(pp)
        
        # Adicionar categorias específicas se aplicável
        if data.get('applies_to') == 'categories' and data.get('category_ids'):
            for category_id in data['category_ids']:
                pc = PromotionCategory(promotion_id=promotion.id, category_id=category_id)
                db.session.add(pc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Promoção criada com sucesso!',
            'promotion': promotion.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin.route('/promotions/<promotion_id>', methods=['GET'])
@login_required
@store_required
def get_promotion(promotion_id):
    """Obter detalhes de uma promoção"""
    store_id = session.get('store_id')
    promotion = Promotion.query.filter_by(id=promotion_id, store_id=store_id).first()
    
    if not promotion:
        return jsonify({'success': False, 'error': 'Promoção não encontrada'}), 404
    
    return jsonify({'success': True, 'promotion': promotion.to_dict()})


@admin.route('/promotions/<promotion_id>', methods=['PUT'])
@login_required
@store_required
def update_promotion(promotion_id):
    """Atualizar promoção"""
    try:
        data = request.get_json()
        store_id = session.get('store_id')
        
        promotion = Promotion.query.filter_by(id=promotion_id, store_id=store_id).first()
        
        if not promotion:
            return jsonify({'success': False, 'error': 'Promoção não encontrada'}), 404
        
        # Atualizar campos
        if 'name' in data:
            promotion.name = data['name']
        if 'description' in data:
            promotion.description = data['description']
        if 'discount_type' in data:
            promotion.discount_type = data['discount_type']
        if 'discount_value' in data:
            promotion.discount_value = float(data['discount_value'])
        if 'min_purchase_amount' in data:
            promotion.min_purchase_amount = float(data['min_purchase_amount'])
        if 'max_discount_amount' in data:
            promotion.max_discount_amount = float(data['max_discount_amount']) if data['max_discount_amount'] else None
        if 'start_date' in data:
            promotion.start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00').replace('+00:00', ''))
        if 'end_date' in data:
            promotion.end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00').replace('+00:00', ''))
        if 'is_active' in data:
            promotion.is_active = data['is_active']
        if 'applies_to' in data:
            promotion.applies_to = data['applies_to']
        
        # Atualizar produtos/categorias se necessário
        if 'applies_to' in data:
            # Limpar associações antigas
            PromotionProduct.query.filter_by(promotion_id=promotion.id).delete()
            PromotionCategory.query.filter_by(promotion_id=promotion.id).delete()
            
            if data['applies_to'] == 'products' and data.get('product_ids'):
                for product_id in data['product_ids']:
                    pp = PromotionProduct(promotion_id=promotion.id, product_id=product_id)
                    db.session.add(pp)
            
            if data['applies_to'] == 'categories' and data.get('category_ids'):
                for category_id in data['category_ids']:
                    pc = PromotionCategory(promotion_id=promotion.id, category_id=category_id)
                    db.session.add(pc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Promoção atualizada com sucesso!',
            'promotion': promotion.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin.route('/promotions/<promotion_id>', methods=['DELETE'])
@login_required
@store_required
def delete_promotion(promotion_id):
    """Excluir promoção"""
    try:
        store_id = session.get('store_id')
        promotion = Promotion.query.filter_by(id=promotion_id, store_id=store_id).first()
        
        if not promotion:
            return jsonify({'success': False, 'error': 'Promoção não encontrada'}), 404
        
        db.session.delete(promotion)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Promoção excluída com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin.route('/promotions/<promotion_id>/toggle', methods=['POST'])
@login_required
@store_required
def toggle_promotion(promotion_id):
    """Ativar/Desativar promoção"""
    try:
        store_id = session.get('store_id')
        promotion = Promotion.query.filter_by(id=promotion_id, store_id=store_id).first()
        
        if not promotion:
            return jsonify({'success': False, 'error': 'Promoção não encontrada'}), 404
        
        promotion.is_active = not promotion.is_active
        db.session.commit()
        
        status = 'ativada' if promotion.is_active else 'desativada'
        return jsonify({
            'success': True,
            'message': f'Promoção {status} com sucesso!',
            'is_active': promotion.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin.route('/coupons')
@login_required
@store_required
def coupons_page():
    """Página de cupons de desconto"""
    return render_template('admin/coupons.html')