import types
from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime, timedelta



class ChatSimulator(QObject):
    test_message = pyqtSignal(str, dict)

    def __init__(self, instance_mock):
        super().__init__()
        self.instance = instance_mock

    def on_chat(self, message: types.SimpleNamespace):
        nick = message.profile.nickname
        id = message.profile.user_id_hash
        time = (message.time+timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        msg = message.content.replace('\n'," ")
        chat = (f"[{time}] <{nick} ({id})> {msg}")
        
        data = {'donation_type': '채팅', 'time': time, 'nick': nick, 'id': id, 'msg': msg}
        self.test_message.emit(chat, data)

    def on_subscription(self, message: types.SimpleNamespace):
        time = (message.time+timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        nick = message.profile.nickname
        id = message.profile.user_id_hash
        month = message.extras.month
        tier_no = message.extras.tier_no
        chatmsg = message.content.replace("\n"," ")
        chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님이 {tier_no}티어 {month}개월 정기구독을 갱신하였습니다! ⭐🟥 기념 메시지: {chatmsg}")
        data = {'donation_type': '구독', 'time': time, 'nick': nick, 'id': id, 'tier': tier_no, 'month': month, 'msg': chatmsg}
        self.test_message.emit(chat, data)
    
    def on_subscription_gift(self, message: types.SimpleNamespace):
        gift_tier_no = message.extras.gift_tier_no
        sender_user_id = message.extras.sender_user_id
        sender_user_nick = ""
        gift_quantity = message.extras.quantity
        if gift_quantity == None: gift_quantity = 1

        if sender_user_id == None or message.profile == None:
            sender_user_nick = "익명의 후원자"
            sec = (message.time+timedelta(hours=9)).strftime("%H%M%S")
            sender_user_id = f"anon{sec}"
        else: sender_user_nick = message.profile.nickname

        try:
            receiver_user_id = message.extras.receiver_user_id
        except:
            receiver_user_id = "(받은이 아이디)"
        
        try:
            receiver_user_nick = message.extras.receiver_user
        except:
            receiver_user_nick = "(받은이 닉네임)"
        
        try:
            selection_type = message.extras.selection_type
        except:
            selection_type = "RANDOM"

        time = (message.time+timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")

        if selection_type == "RANDOM": # 랜덤 선물
            chat = (f"[{time}] <{sender_user_nick} ({sender_user_id})> 🟥⭐ {sender_user_nick}님이 {gift_tier_no}티어 구독권 {gift_quantity}개를 선물했습니다! ⭐🟥")
            data = {'donation_type': '구독선물', 'time': time, 'nick': sender_user_nick, 'id': sender_user_id, 'selection_type': selection_type, 'quantity': gift_quantity, 'tier': gift_tier_no}
        else: # 지정 선물
            chat = (f"[{time}] <{sender_user_nick} ({sender_user_id})> 🟥⭐ {sender_user_nick}님이 {gift_tier_no}티어 구독권을 {receiver_user_nick}에게 선물했습니다! ⭐🟥")
            data = {'donation_type': '구독선물', 'time': time, 'nick': sender_user_nick, 'id': sender_user_id, 'selection_type': selection_type, 'receiver_nick': receiver_user_nick, 'quantity': gift_quantity, 'tier': gift_tier_no}
        self.test_message.emit(chat, data)

    def on_donation(self, message: types.SimpleNamespace):
        time = (message.time+timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
        sec = (message.time+timedelta(hours=9)).strftime("%H%M%S")
        if message.extras.is_anonymous:
            nick, id = "익명의 후원자", f"anon{sec}"
        else:
            nick, id = message.profile.nickname, message.profile.user_id_hash
        
        cheese_num = message.extras.pay_amount

        if message.extras.donation_type == 'VIDEO':
            videotitle = message.content
            tier = str(message.profile.tier)
            chat = (f"[{time}] <{nick} ({id})> 🟥⭐ 영상후원 {cheese_num}치즈 후원! ⭐🟥 영상 제목: {videotitle}")
            data = {'donation_type': '영상후원', 'time': time, 'nick': nick, 'id': id, 'cheese': cheese_num, 'title': videotitle, 'tier': tier, 'sec': cheese_num}
            self.test_message.emit(chat, data)
        
        elif message.extras.donation_type == 'CHAT':
            chatmsg = message.content.replace('\n', " ")
            chat = (f"[{time}] <{nick} ({id})> 🟥⭐ 일반후원 {cheese_num}치즈 후원! ⭐🟥 후원 메시지: {chatmsg}")
            data = {'donation_type': '치즈', 'time': time, 'nick': nick, 'id': id, 'msg': chatmsg, 'cheese': cheese_num}
            self.test_message.emit(chat, data)

    def on_mission_completed(self, mission: types.SimpleNamespace):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if mission.is_anonymous:
            nick, id = "익명의 후원자", "anon_mission"
        else:
            nick, id = mission.nickname, mission.user_id_hash
        cheese_num = mission.total_pay_amount
        pnum = mission.participation_count

        if mission.success:
            chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님 외 {pnum}명의 미션 성공! {cheese_num}치즈 획득! ⭐🟥 미션 내용: {mission.mission_text}")
            data = {'donation_type': '미션성공', 'time': time, 'nick': nick, 'id': id, 'cheese': cheese_num, 'pnum': pnum, 'msg': mission.mission_text}
            self.test_message.emit(chat, data)
        else:
            chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님 외 {pnum}명의 미션 실패! {cheese_num}치즈 획득 실패! ⭐🟥 미션 내용: {mission.mission_text}")
            data = {'donation_type': '미션실패', 'time': time, 'nick': nick, 'id': id, 'cheese': cheese_num, 'pnum': pnum, 'msg': mission.mission_text}
            self.test_message.emit(chat, data)

    def on_mission_pending(self, mission: types.SimpleNamespace):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if mission.is_anonymous:
            nick, id = "익명의 후원자", "anon_mission"
        else:
            nick, id = mission.nickname, mission.user_id_hash
        cheese_num = mission.total_pay_amount
        chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님의 미션 대기 중! {cheese_num}치즈 후원! ⭐🟥 미션 내용: {mission.mission_text}")
        data = {'donation_type': '미션대기', 'time': time, 'nick': nick, 'id': id, 'cheese': cheese_num, 'msg': mission.mission_text}
        self.test_message.emit(chat, data)

    def on_mission_approved(self, mission: types.SimpleNamespace):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if mission.is_anonymous:
            nick, id = "익명의 후원자", "anon_mission"
        else:
            nick, id = mission.nickname, mission.user_id_hash
        cheese_num = mission.total_pay_amount
        chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님의 미션 수락! 미션금 총 {cheese_num}치즈 ⭐🟥 미션 내용: {mission.mission_text}")
        data = {'donation_type': '미션수락', 'time': time, 'nick': nick, 'id': id, 'cheese': cheese_num, 'msg': mission.mission_text}
        self.test_message.emit(chat, data)

    def on_mission_update_cost(self, mission: types.SimpleNamespace):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if mission.is_anonymous:
            nick, id = "익명의 후원자", "anon_mission"
        else:
            nick, id = mission.nickname, mission.user_id_hash
        cheese_num = mission.pay_amount
        cheese_num_sum = mission.total_pay_amount
        chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님이 미션 추가금 {cheese_num}치즈 후원! 미션금 총 {cheese_num_sum}치즈 ⭐🟥 미션 내용: {mission.mission_text}")
        data = {'donation_type': '미션', 'time': time, 'nick': nick, 'id': id, 'cheese': cheese_num, 'sum': cheese_num_sum, 'msg': mission.mission_text}
        self.test_message.emit(chat, data)
    
    def on_mission_rejected(self, mission: types.SimpleNamespace):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if mission.is_anonymous:
            nick, id = "익명의 후원자", "anon_mission"
        else:
            nick, id = mission.nickname, mission.user_id_hash
        cheese_num = mission.total_pay_amount
        chat = (f"[{time}] <{nick} ({id})> 🟥⭐ {nick}님의 미션 거절! {cheese_num}치즈 획득 실패! ⭐🟥 미션 내용: {mission.mission_text}")
        data = {'donation_type': '미션거절', 'time': time, 'nick': nick, 'id': id, 'cheese': cheese_num, 'msg': mission.mission_text}
        self.test_message.emit(chat, data)

