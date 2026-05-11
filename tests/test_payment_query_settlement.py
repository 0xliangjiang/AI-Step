import asyncio
import sys
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from time_utils import get_china_now
import main


class _Field:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return (self.name, other)

    def __hash__(self):
        return hash(self.name)


class _FakePaymentOrderModel:
    order_no = _Field("order_no")
    id = _Field("id")
    status = _Field("status")
    transaction_id = _Field("transaction_id")
    paid_at = _Field("paid_at")


class _FakeUserModel:
    user_key = _Field("user_key")


class _FakeOrder:
    id = 1

    def __init__(self):
        self.order_no = "ORDER123"
        self.user_key = "openid_123"
        self.days = 30
        self.amount = 990
        self.status = "pending"
        self.transaction_id = None
        self.paid_at = None

    def to_dict(self):
        return {
            "order_no": self.order_no,
            "user_key": self.user_key,
            "days": self.days,
            "status": self.status,
            "transaction_id": self.transaction_id,
        }


class _FakeUser:
    def __init__(self):
        self.user_key = "openid_123"
        self.vip_expire_at = get_china_now() + timedelta(days=2)


class _FakeQuery:
    def __init__(self, session, model):
        self.session = session
        self.model = model

    def filter(self, *conditions):
        return self

    def first(self):
        if self.model is _FakePaymentOrderModel:
            return self.session.order
        if self.model is _FakeUserModel:
            return self.session.user
        return None

    def update(self, values, synchronize_session=False):
        if self.model is not _FakePaymentOrderModel:
            return 0
        if self.session.order.status != "pending":
            return 0
        for field, value in values.items():
            setattr(self.session.order, field.name, value)
        return 1


class _FakeSession:
    def __init__(self):
        self.order = _FakeOrder()
        self.user = _FakeUser()

    def query(self, model):
        return _FakeQuery(self, model)


class _FakeSessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


class PaymentQuerySettlementTests(unittest.TestCase):
    def test_query_settles_pending_order_when_wechat_reports_success(self):
        session = _FakeSession()
        original_expire = session.user.vip_expire_at

        with patch.object(main, "PaymentOrder", _FakePaymentOrderModel), \
                patch.object(main, "User", _FakeUserModel), \
                patch.object(main, "get_db_session", return_value=_FakeSessionContext(session)), \
                patch.object(main.wechat_pay, "query_order", return_value={
                    "success": True,
                    "trade_state": "SUCCESS",
                    "transaction_id": "wx_txn_123",
                    "trade_state_desc": "支付成功",
                }):
            response = asyncio.run(main.query_payment_order("ORDER123", user_key="openid_123"))

        self.assertTrue(response["success"])
        self.assertEqual("paid", response["status"])
        self.assertEqual("paid", session.order.status)
        self.assertEqual("wx_txn_123", session.order.transaction_id)
        self.assertEqual(original_expire + timedelta(days=30), session.user.vip_expire_at)

    def test_query_paid_order_does_not_grant_days_again(self):
        session = _FakeSession()
        session.order.status = "paid"
        session.order.transaction_id = "wx_txn_existing"
        original_expire = session.user.vip_expire_at

        with patch.object(main, "PaymentOrder", _FakePaymentOrderModel), \
                patch.object(main, "User", _FakeUserModel), \
                patch.object(main, "get_db_session", return_value=_FakeSessionContext(session)), \
                patch.object(main.wechat_pay, "query_order") as query_order:
            response = asyncio.run(main.query_payment_order("ORDER123", user_key="openid_123"))

        self.assertTrue(response["success"])
        self.assertEqual("paid", response["status"])
        self.assertEqual("paid", session.order.status)
        self.assertEqual("wx_txn_existing", session.order.transaction_id)
        self.assertEqual(original_expire, session.user.vip_expire_at)
        query_order.assert_not_called()


if __name__ == "__main__":
    unittest.main()
