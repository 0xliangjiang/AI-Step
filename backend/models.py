# -*- coding: utf-8 -*-
"""
数据库模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL

Base = declarative_base()


class Admin(Base):
    """管理员表"""
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password = Column(String(255), nullable=False, comment="密码哈希")
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_key = Column(String(100), unique=True, nullable=True, comment="用户唯一标识（批量注册时为空）")
    zepp_email = Column(String(255), comment="Zepp注册邮箱")
    zepp_password = Column(String(255), comment="Zepp密码")
    zepp_userid = Column(String(100), comment="Zepp用户ID")
    bind_status = Column(Integer, default=0, comment="绑定状态: 0未绑定 1已绑定")
    vip_expire_at = Column(DateTime, comment="会员过期时间")
    login_token = Column(Text, comment="登录Token缓存")
    app_token = Column(Text, comment="App Token缓存")
    token_updated_at = Column(DateTime, comment="Token更新时间")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        # 判断会员是否有效
        is_vip = False
        if self.vip_expire_at:
            is_vip = self.vip_expire_at > datetime.now()

        return {
            "id": self.id,
            "user_key": self.user_key,
            "zepp_email": self.zepp_email,
            "zepp_userid": self.zepp_userid,
            "bind_status": self.bind_status,
            "vip_expire_at": self.vip_expire_at.strftime("%Y-%m-%d %H:%M:%S") if self.vip_expire_at else None,
            "is_vip": is_vip,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }


class StepRecord(Base):
    """刷步记录表"""
    __tablename__ = "step_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_key = Column(String(100), nullable=False, index=True)
    steps = Column(Integer, nullable=False)
    status = Column(String(20), comment="success/failed")
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_key": self.user_key,
            "steps": self.steps,
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }


class ScheduledTask(Base):
    """定时刷步任务表"""
    __tablename__ = "scheduled_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_key = Column(String(100), nullable=False, index=True, comment="用户标识")
    target_steps = Column(Integer, nullable=False, comment="目标步数")
    start_hour = Column(Integer, default=8, comment="开始时间（小时，0-23）")
    end_hour = Column(Integer, default=21, comment="结束时间（小时，0-23）")
    status = Column(String(20), default="active", comment="状态: active/paused/cancelled")
    current_steps = Column(Integer, default=0, comment="当天已刷步数")
    current_step_index = Column(Integer, default=0, comment="当前执行到第几个时间段")
    last_run_at = Column(DateTime, comment="上次执行时间")
    last_run_date = Column(String(10), comment="上次执行日期 YYYY-MM-DD")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_key": self.user_key,
            "target_steps": self.target_steps,
            "start_hour": self.start_hour,
            "end_hour": self.end_hour,
            "status": self.status,
            "current_steps": self.current_steps,
            "current_step_index": self.current_step_index,
            "last_run_at": self.last_run_at.strftime("%Y-%m-%d %H:%M:%S") if self.last_run_at else None,
            "last_run_date": self.last_run_date,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None
        }


class Card(Base):
    """卡密表"""
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    card_key = Column(String(32), unique=True, nullable=False, index=True, comment="卡密")
    days = Column(Integer, nullable=False, comment="天数")
    status = Column(String(20), default="unused", comment="状态: unused/used")
    used_by = Column(String(100), comment="使用者user_key")
    used_at = Column(DateTime, comment="使用时间")
    created_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "card_key": self.card_key,
            "days": self.days,
            "status": self.status,
            "used_by": self.used_by,
            "used_at": self.used_at.strftime("%Y-%m-%d %H:%M:%S") if self.used_at else None,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }


# 数据库连接
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(engine)


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
