import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AdRewardFlowTests(unittest.TestCase):
    def test_backend_watch_ad_endpoint_is_enabled_and_uses_china_time(self):
        main_py = (ROOT / 'backend' / 'main.py').read_text(encoding='utf-8')

        # 接口已启用（取消注释）
        self.assertIn('@app.post("/api/user/watch-ad", response_model=AdWatchResponse)', main_py)
        self.assertIn('@app.get("/api/user/ad-config")', main_py)
        self.assertIn('@app.get("/api/user/ad-status", response_model=AdWatchResponse)', main_py)

        # POST 走 Pydantic body 模型而非 query 参数
        self.assertIn('class WatchAdRequest(BaseModel):', main_py)
        self.assertIn('async def watch_ad(request: WatchAdRequest):', main_py)

        # 审核模式拦截
        self.assertIn('if REVIEW_MODE:', main_py)

        # 广告逻辑统一使用中国时区，不再用 datetime.now()
        watch_section = main_py.split('# ==================== 广告相关接口 ====================')[1]
        watch_section = watch_section.split('# ==================== 广告相关接口结束')[0]
        self.assertIn('get_china_now()', watch_section)
        self.assertNotIn('datetime.now()', watch_section)

    def test_brush_step_returns_vip_expired_flag_with_requested_steps(self):
        skills_py = (ROOT / 'backend' / 'skills.py').read_text(encoding='utf-8')

        self.assertIn("'vip_expired': True", skills_py)
        self.assertIn("'requested_steps': steps", skills_py)

    def test_ad_daily_limit_defaults_to_one(self):
        config_py = (ROOT / 'backend' / 'config.py').read_text(encoding='utf-8')

        self.assertIn('AD_DAILY_LIMIT = int(os.getenv("AD_DAILY_LIMIT", 1))', config_py)

    def test_chat_page_shows_renew_or_watch_ad_modal_on_expired_vip(self):
        chat_js = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.js').read_text(encoding='utf-8')
        chat_wxml = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.wxml').read_text(encoding='utf-8')
        chat_wxss = (ROOT / 'miniprogram' / 'pages' / 'chat' / 'chat.wxss').read_text(encoding='utf-8')

        # 状态字段
        self.assertIn('showVipModal: false', chat_js)
        self.assertIn('pendingBrushSteps: 0', chat_js)
        self.assertIn('watchingAd: false', chat_js)

        # 流程方法
        self.assertIn('checkVipExpired(functionResult)', chat_js)
        self.assertIn('this.checkVipExpired(res.function_result)', chat_js)
        self.assertIn('goRenewVip()', chat_js)
        self.assertIn('watchAdForVip()', chat_js)
        self.assertIn('claimVipReward()', chat_js)
        self.assertIn('resendBrush(steps)', chat_js)
        self.assertIn('closeVipModal()', chat_js)

        # 激励视频广告调用与领取接口
        self.assertIn('wx.createRewardedVideoAd', chat_js)
        self.assertIn("api.request('/user/watch-ad', 'POST', {})", chat_js)
        self.assertIn('adunit-xxxxxxxxxxxxxxxx', chat_js)
        self.assertIn('广告位未配置', chat_js)

        # 弹窗结构
        self.assertIn('wx:if="{{showVipModal}}"', chat_wxml)
        self.assertIn('bindtap="goRenewVip"', chat_wxml)
        self.assertIn('bindtap="watchAdForVip"', chat_wxml)
        self.assertIn('bindtap="closeVipModal"', chat_wxml)
        self.assertIn('看视频领今日会员', chat_wxml)
        self.assertIn('续费会员', chat_wxml)

        # 样式
        self.assertIn('.vip-modal-options', chat_wxss)
        self.assertIn('.vip-option', chat_wxss)

        # 不得引入审核禁词
        self.assertNotIn('当前版本暂未开放', chat_js)

    def test_app_has_configured_rewarded_video_ad_unit(self):
        app_js = (ROOT / 'miniprogram' / 'app.js').read_text(encoding='utf-8')

        self.assertIn('rewardedVideoAdUnitId', app_js)
        self.assertIn("rewardedVideoAdUnitId: 'adunit-02cfdc01b28fc37e'", app_js)
        # 真实广告位已配置，不应再保留占位符
        self.assertNotIn('adunit-xxxxxxxxxxxxxxxx', app_js)


if __name__ == '__main__':
    unittest.main()
