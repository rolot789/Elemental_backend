from flask import Blueprint, jsonify, request, session
from datetime import datetime, date
from src.models import db, User, Room, Booking

api_bp = Blueprint('api', __name__)

# 로그인 API
@api_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    student_id = data.get('student_id', '').strip()
    
    if not student_id:
        return jsonify({'error': '학번을 입력해주세요.'}), 400
    
    user = User.login_or_create(student_id)
    if not user:
        return jsonify({'error': '올바른 학번을 입력해주세요. (10자리 숫자)'}), 400
    
    if user.is_banned:
        return jsonify({'error': '이용이 제한된 사용자입니다.'}), 403
    
    # 세션에 사용자 정보 저장
    session['user_id'] = user.id
    session['student_id'] = user.student_id
    session['is_admin'] = user.is_admin
    
    return jsonify({
        'success': True,
        'user': user.to_dict()
    })

# 로그아웃 API
@api_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

# 현재 사용자 정보 조회
@api_bp.route('/me', methods=['GET'])
def get_current_user():
    if 'user_id' not in session:
        return jsonify({'error': '로그인이 필요합니다.'}), 401
    
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': '사용자를 찾을 수 없습니다.'}), 404
    
    return jsonify(user.to_dict())

# 스터디룸 목록 조회
@api_bp.route('/rooms', methods=['GET'])
def get_rooms():
    rooms = Room.query.filter_by(is_active=True).all()
    return jsonify([room.to_dict() for room in rooms])

# 특정 날짜의 예약 현황 조회
@api_bp.route('/bookings', methods=['GET'])
def get_bookings():
    booking_date_str = request.args.get('date', date.today().isoformat())
    
    try:
        booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': '올바른 날짜 형식이 아닙니다. (YYYY-MM-DD)'}), 400
    
    bookings = Booking.query.filter_by(booking_date=booking_date).all()
    return jsonify([booking.to_dict() for booking in bookings])

# 새 예약 생성
@api_bp.route('/bookings', methods=['POST'])
def create_booking():
    if 'user_id' not in session:
        return jsonify({'error': '로그인이 필요합니다.'}), 401
    
    data = request.json
    room_id = data.get('room_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    team_members = data.get('team_members', [])
    booking_date = date.today()  # 당일 예약만 가능
    
    # 입력값 검증
    if not all([room_id, start_time, end_time]):
        return jsonify({'error': '필수 정보가 누락되었습니다.'}), 400
    
    # 스터디룸 존재 확인
    room = Room.query.get(room_id)
    if not room or not room.is_active:
        return jsonify({'error': '존재하지 않는 스터디룸입니다.'}), 404
    
    # 시간 충돌 검사
    if Booking.check_time_conflict(room_id, booking_date, start_time, end_time):
        return jsonify({'error': '해당 시간에 이미 예약이 있습니다.'}), 409
    
    # 일일 예약 시간 제한 검사 (4시간)
    student_id = session['student_id']
    current_hours = Booking.get_user_daily_hours(student_id, booking_date)
    
    # 새 예약 시간 계산
    start_hour = start_time // 100
    start_min = start_time % 100
    end_hour = end_time // 100
    end_min = end_time % 100
    new_duration = (end_hour * 60 + end_min) - (start_hour * 60 + start_min)
    
    if current_hours + (new_duration / 60) > 4:
        return jsonify({'error': '하루 최대 4시간까지만 예약 가능합니다.'}), 400
    
    # 예약 생성
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

# 예약 취소
@api_bp.route('/bookings/<int:booking_id>', methods=['DELETE'])
def cancel_booking(booking_id):
    if 'user_id' not in session:
        return jsonify({'error': '로그인이 필요합니다.'}), 401
    
    booking = Booking.query.get_or_404(booking_id)
    
    # 본인 예약이거나 관리자인지 확인
    if booking.student_id != session['student_id'] and not session.get('is_admin'):
        return jsonify({'error': '권한이 없습니다.'}), 403
    
    db.session.delete(booking)
    db.session.commit()
    
    return jsonify({'success': True})

# 내 예약 조회
@api_bp.route('/my-bookings', methods=['GET'])
def get_my_bookings():
    if 'user_id' not in session:
        return jsonify({'error': '로그인이 필요합니다.'}), 401
    
    student_id = session['student_id']
    bookings = Booking.query.filter_by(student_id=student_id).order_by(Booking.booking_date.desc(), Booking.start_time.asc()).all()
    
    return jsonify([booking.to_dict() for booking in bookings])

