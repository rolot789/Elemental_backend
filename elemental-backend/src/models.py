from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(10), unique=True, nullable=False)  # 학번
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_banned = db.Column(db.Boolean, nullable=False, default=False)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.student_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'is_admin': self.is_admin,
            'is_banned': self.is_banned,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def login_or_create(student_id):
        """학번으로 로그인하거나 새 사용자 생성"""
        # 관리자 체크
        if student_id == "관리자1234":
            user = User.query.filter_by(student_id=student_id).first()
            if not user:
                user = User(student_id=student_id, is_admin=True)
                db.session.add(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return user
        
        # 일반 사용자 (학번 10자리 체크)
        if len(student_id) != 10 or not student_id.isdigit():
            return None
            
        user = User.query.filter_by(student_id=student_id).first()
        if not user:
            user = User(student_id=student_id)
            db.session.add(user)
        
        user.last_login = datetime.utcnow()
        db.session.commit()
        return user

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=4)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'capacity': self.capacity,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def create_default_rooms():
        """기본 스터디룸 6개 생성"""
        if Room.query.count() == 0:
            for i in range(1, 7):
                room = Room(name=f'스터디룸 {i}', capacity=4)
                db.session.add(room)
            db.session.commit()

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    student_id = db.Column(db.String(10), nullable=False)  # 학번
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Integer, nullable=False)  # 시간을 정수로 저장 (9시 = 9, 13시 30분 = 1330)
    end_time = db.Column(db.Integer, nullable=False)
    team_members = db.Column(db.Text)  # JSON 형태로 팀원 정보 저장
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def to_dict(self):
        team_members_data = []
        if self.team_members:
            try:
                team_members_data = json.loads(self.team_members)
            except:
                team_members_data = []
                
        return {
            'id': self.id,
            'room_id': self.room_id,
            'student_id': self.student_id,
            'booking_date': self.booking_date.isoformat() if self.booking_date else None,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'team_members': team_members_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def set_team_members(self, members_list):
        """팀원 정보를 JSON으로 저장"""
        self.team_members = json.dumps(members_list, ensure_ascii=False)
    
    def get_team_members(self):
        """팀원 정보를 리스트로 반환"""
        if self.team_members:
            try:
                return json.loads(self.team_members)
            except:
                return []
        return []
    
    @staticmethod
    def get_user_daily_hours(student_id, booking_date):
        """특정 사용자의 특정 날짜 총 예약 시간 계산"""
        bookings = Booking.query.filter_by(
            student_id=student_id,
            booking_date=booking_date
        ).all()
        
        total_hours = 0
        for booking in bookings:
            start_hour = booking.start_time // 100
            start_min = booking.start_time % 100
            end_hour = booking.end_time // 100
            end_min = booking.end_time % 100
            
            duration = (end_hour * 60 + end_min) - (start_hour * 60 + start_min)
            total_hours += duration / 60
            
        return total_hours
    
    @staticmethod
    def check_time_conflict(room_id, booking_date, start_time, end_time, exclude_booking_id=None):
        """시간 충돌 검사"""
        query = Booking.query.filter_by(
            room_id=room_id,
            booking_date=booking_date
        )
        
        if exclude_booking_id:
            query = query.filter(Booking.id != exclude_booking_id)
            
        existing_bookings = query.all()
        
        for booking in existing_bookings:
            # 시간 겹침 검사
            if not (end_time <= booking.start_time or start_time >= booking.end_time):
                return True
        return False

