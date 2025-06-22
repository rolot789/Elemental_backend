from flask import Blueprint, jsonify, request, session
from datetime import datetime, date
from src.models import db, User, Room, Booking

admin_bp = Blueprint('admin', __name__)

def require_admin():
    """관리자 권한 확인 데코레이터"""
    if 'user_id' not in session:
        return jsonify({'error': '로그인이 필요합니다.'}), 401
    
    if not session.get('is_admin'):
        return jsonify({'error': '관리자 권한이 필요합니다.'}), 403
    
    return None

# 전체 예약 현황 조회
@admin_bp.route('/bookings', methods=['GET'])
def admin_get_all_bookings():
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    booking_date_str = request.args.get('date')
    if booking_date_str:
        try:
            booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
            bookings = Booking.query.filter_by(booking_date=booking_date).all()
        except ValueError:
            return jsonify({'error': '올바른 날짜 형식이 아닙니다. (YYYY-MM-DD)'}), 400
    else:
        bookings = Booking.query.all()
    
    return jsonify([booking.to_dict() for booking in bookings])

# 강제 예약 생성
@admin_bp.route('/bookings', methods=['POST'])
def admin_create_booking():
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    data = request.json
    room_id = data.get('room_id')
    student_id = data.get('student_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    booking_date_str = data.get('booking_date', date.today().isoformat())
    team_members = data.get('team_members', [])
    
    try:
        booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': '올바른 날짜 형식이 아닙니다. (YYYY-MM-DD)'}), 400
    
    # 입력값 검증
    if not all([room_id, student_id, start_time, end_time]):
        return jsonify({'error': '필수 정보가 누락되었습니다.'}), 400
    
    # 스터디룸 존재 확인
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': '존재하지 않는 스터디룸입니다.'}), 404
    
    # 예약 생성 (관리자는 제한 무시)
    booking = Booking(
        room_id=room_id,
        student_id=student_id,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time
    )
    
    if team_members:
        booking.set_team_members(team_members)
    
    db.session.add(booking)
    db.session.commit()
    
    return jsonify(booking.to_dict()), 201

# 강제 예약 취소
@admin_bp.route('/bookings/<int:booking_id>', methods=['DELETE'])
def admin_cancel_booking(booking_id):
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    booking = Booking.query.get_or_404(booking_id)
    db.session.delete(booking)
    db.session.commit()
    
    return jsonify({'success': True})

# 사용자 관리 - 전체 사용자 조회
@admin_bp.route('/users', methods=['GET'])
def admin_get_users():
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

# 사용자 관리 - 특정 사용자 조회
@admin_bp.route('/users/<student_id>', methods=['GET'])
def admin_get_user(student_id):
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    user = User.query.filter_by(student_id=student_id).first_or_404()
    bookings = Booking.query.filter_by(student_id=student_id).order_by(Booking.booking_date.desc()).all()
    
    return jsonify({
        'user': user.to_dict(),
        'bookings': [booking.to_dict() for booking in bookings]
    })

# 사용자 이용 제한/해제
@admin_bp.route('/users/<student_id>/ban', methods=['POST'])
def admin_ban_user(student_id):
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    user = User.query.filter_by(student_id=student_id).first_or_404()
    data = request.json
    is_banned = data.get('is_banned', True)
    
    user.is_banned = is_banned
    db.session.commit()
    
    return jsonify(user.to_dict())

# 스터디룸 관리 - 전체 스터디룸 조회
@admin_bp.route('/rooms', methods=['GET'])
def admin_get_rooms():
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    rooms = Room.query.all()
    return jsonify([room.to_dict() for room in rooms])

# 스터디룸 관리 - 스터디룸 수정
@admin_bp.route('/rooms/<int:room_id>', methods=['PUT'])
def admin_update_room(room_id):
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    room = Room.query.get_or_404(room_id)
    data = request.json
    
    room.name = data.get('name', room.name)
    room.capacity = data.get('capacity', room.capacity)
    room.is_active = data.get('is_active', room.is_active)
    
    db.session.commit()
    return jsonify(room.to_dict())

# 스터디룸 관리 - 새 스터디룸 추가
@admin_bp.route('/rooms', methods=['POST'])
def admin_create_room():
    auth_error = require_admin()
    if auth_error:
        return auth_error
    
    data = request.json
    name = data.get('name')
    capacity = data.get('capacity', 4)
    
    if not name:
        return jsonify({'error': '스터디룸 이름이 필요합니다.'}), 400
    
    room = Room(name=name, capacity=capacity)
    db.session.add(room)
    db.session.commit()
    
    return jsonify(room.to_dict()), 201

