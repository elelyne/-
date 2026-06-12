import os
import json
import random
import secrets
from flask import render_template, session
from datetime import datetime
from datetime import date, datetime
from flask import jsonify, request, session
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask import Flask, render_template, session, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template


app = Flask(__name__)  #用FLASK架設後端
app.config['SECRET_KEY'] = 'mindapp_super_secret_key_2026' #伺服器密碼鎖
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db' #資料庫路徑
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # 關閉SQLAlchemy的修改追蹤機制減少記憶體消耗提升伺服器執行效率
db = SQLAlchemy(app)  # 把FLASK綁到SQLAlchemy啟用資料庫功能

#使用者資料庫模型
class User(UserMixin, db.Model):  #SQL定義類別資料表 #繼承UserMixin(登入驗證)、db.Model(資料表)
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True) #建立id欄位
    username = db.Column(db.String(50), unique=True, nullable=False) # 帳號(不能重複/留空)
    password = db.Column(db.String(100), nullable=False)            # 密碼
    nickname = db.Column(db.String(50), nullable=False)             # 用戶名
    coins = db.Column(db.Integer, default=100)                      # 金幣
    last_checkin = db.Column(db.Date, nullable=True)                # 上次簽到日
    last_task_date = db.Column(db.Date, nullable=True)              # 上次任務日
    
    height = db.Column(db.Float, nullable=True)       #身高
    weight = db.Column(db.Float, nullable=True)       #體重
    gender = db.Column(db.String(10), nullable=True)  #性別
    water = db.Column(db.Integer, default=0)          #今日喝水量
    steps = db.Column(db.Integer, default=0)          #今日步數
    diary = db.Column(db.Text, nullable=True)         #日記(允許空)
    current_video = db.Column(db.String(255), nullable=True, default=None) #影片
    highest_score = db.Column(db.Integer, default=0, nullable=True) #遊戲最高分數紀錄

# 每日歷史紀錄資料庫模型
class DailyRecord(db.Model):  #定義DailyRecord類別記錄每日任務數據
    __tablename__ = 'daily_record'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    water = db.Column(db.Integer, default=0)
    steps = db.Column(db.Integer, default=0)
    diary = db.Column(db.Text, nullable=True)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='_user_date_uc'),)
#user_id&date在資料庫只能有一個
# 好友關係與邀請資料庫模型 
class Friendship(db.Model): #好友關係資料表
    __tablename__ = 'friendship'
    
    id = db.Column(db.Integer, primary_key=True) #主鍵，自動增序號
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)   # 寄出邀請的人/外鍵指向 user.id
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # 接收邀請的人/外鍵指向 user.id
    status = db.Column(db.String(20), default='pending')                       # 狀態：pending, accepted

    sender = db.relationship('User', foreign_keys=[user_id], backref='sent_invites')  #可以直接用user.sent_invites查出送出了哪些好友邀請
    receiver = db.relationship('User', foreign_keys=[friend_id], backref='received_invites')#查出接受了哪些好友邀請



# 登入管理器配置
login_manager = LoginManager() #登入管理
login_manager.init_app(app) #登入管理器正式註冊掛到Flask網站
login_manager.login_view = 'login'

@login_manager.user_loader  #路徑 load_user處理
def load_user(user_id): #接收瀏覽器傳過來的user_id
    return User.query.get(int(user_id)) #去資料庫找用戶資料

# 認證與大廳系統
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])  #註冊路徑
def register():
    if request.method == 'POST':  #使用者提交註冊
        username = request.form.get('username')  #抓取填的帳號
        password = request.form.get('password')  #抓取填的密碼
        nickname = request.form.get('nickname')  #抓取填的暱稱
        
        if User.query.filter_by(username=username).first():  #User資料庫查帳號是否重疊
            flash('此帳號已被佔用！')
            return redirect(url_for('register')) #註冊失敗重新整理註冊頁面
        #密碼加密
        new_user = User(
            username=username, 
            password=generate_password_hash(password), 
            nickname=nickname
        )
        db.session.add(new_user)
        db.session.commit()
        flash('註冊成功！請登入')
        return redirect(url_for('login')) #引導去登入頁面
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST']) 
def login():
    if request.method == 'POST':   #使用者登入
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):  #使用者填的密碼跟資料庫裡的加密亂碼做對比
            login_user(user)
            return redirect(url_for('lobby'))
        flash('帳號或密碼錯誤！')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/lobby')
@login_required
def lobby():
    today = date.today()
    today_str = today.strftime('%Y-%m-%d') #把日期轉成字串
    record = DailyRecord.query.filter_by(user_id=current_user.id, date=today_str).first()
    
    has_checked_in = (current_user.last_checkin == today) #判定簽到狀態
    has_done_task = (record.steps >= 1) if record else False #判定任務狀態
    
    #預設影片
    default_video = "https://www.youtube.com/embed/aqz-KE-bpKQ"
    if current_user and hasattr(current_user, 'current_video') and current_user.current_video:
        lobby_video = current_user.current_video
    else:
        lobby_video = default_video

    return render_template('lobby.html', 
                           user=current_user, 
                           has_checked_in=has_checked_in, 
                           has_done_task=has_done_task,
                           default_video=lobby_video) #回傳到大廳頁面

# 社交系統
@app.route('/api/invite_friend', methods=['POST'])
@login_required
def invite_friend():
    data = request.get_json() or {}
    friend_name = data.get('friend_name', '').strip()
    
    if not friend_name:
        return jsonify({'success': False, 'message': '請輸入好友的用戶名或帳號！'}), 400
    #搜尋目標    
    target_user = User.query.filter((User.username == friend_name) | (User.nickname == friend_name)).first()
    if not target_user:  #若查不到人
        return jsonify({'success': False, 'message': f'找不到用戶【{friend_name}】！'}), 404
        
    if target_user.id == current_user.id: #防呆
        return jsonify({'success': False, 'message': '不能加自己為好友喔！'}), 400

    already_friends = Friendship.query.filter( #Friendship表看有沒有舊紀錄
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == target_user.id)) |
        ((Friendship.user_id == target_user.id) & (Friendship.friend_id == current_user.id))
    ).first()
    
    if already_friends: #重複加好友或正在審核中
        if already_friends.status == 'pending':
            return jsonify({'success': False, 'message': '邀請審核中或您已收到對方的邀請，請勿重複發送！'}), 400
        return jsonify({'success': False, 'message': '你們已經是好友囉！'}), 400

    new_invite = Friendship(user_id=current_user.id, friend_id=target_user.id, status='pending')
    db.session.add(new_invite)  #放進資料庫
    db.session.commit()  #存檔
    
    return jsonify({'success': True, 'message': f'已向【{target_user.nickname}】發送好友邀請！等待對方同意。'})

@app.route('/api/get_invitations', methods=['GET']) #前端畫面的好友申請列表抓資料用
@login_required
def get_invitations(): #Friendship表裡狀態是pending且同個接收人的資料
    invitations = Friendship.query.filter_by(friend_id=current_user.id, status='pending').all()
    results = [{'invite_id': i.id, 'sender_nickname': i.sender.nickname} for i in invitations] #邀請編號、是誰送的暱稱
    return jsonify({'success': True, 'invitations': results}) #同意/拒絕

@app.route('/api/accept_friend', methods=['POST'])
@login_required
def accept_friend():
    data = request.get_json() or {}
    invite_id = data.get('invite_id')
    
    invite = Friendship.query.get(invite_id) #Friendship表查出這筆紀錄
    if not invite or invite.friend_id != current_user.id: #若紀錄不存在
        return jsonify({'success': False, 'message': '找不到該筆好友邀請'}), 404
        
    invite.status = 'accepted'
    db.session.commit()
    #成為好友pending修改成accepted並存入database.db
    #在Friendship表加入sender，找出對方的暱稱回傳同意/拒絕
    return jsonify({'success': True, 'message': f'已同意與【{invite.sender.nickname}】成為好友！'})

@app.route('/api/reject_friend', methods=['POST'])  #拒絕好友邀請
@login_required
def reject_friend():
    data = request.get_json() or {}
    invite_id = data.get('invite_id')
    
    invite = Friendship.query.get(invite_id)
    if not invite or invite.friend_id != current_user.id:
        return jsonify({'success': False, 'message': '找不到該筆好友邀請'}), 404
        
    db.session.delete(invite)  #刪除這一列紀錄
    db.session.commit()  #存檔後database.db刪除裡pending
    return jsonify({'success': True, 'message': '已拒絕該好友邀請。'})

@app.route('/api/get_friends', methods=['GET'])  #獲取正式好友名單
@login_required
def get_friends(): #去Friendship表找資料，條件必須同時滿足A(寄送或接收人是自己)與B(狀態已經同意)
    friendships = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)) & 
        (Friendship.status == 'accepted')
    ).all()
    
    friend_list = [] #空列表存好友名單
    for f in friendships:
        if f.user_id == current_user.id:
            friend_list.append({'id': f.receiver.id, 'nickname': f.receiver.nickname})
        else:
            friend_list.append({'id': f.sender.id, 'nickname': f.sender.nickname})
            
    return jsonify({'success': True, 'friends': friend_list})

# 每日任務與日誌系統
@app.route('/checkin', methods=['POST'])    #每日簽到系統 
@login_required
def checkin():
    today = date.today()
    if current_user.last_checkin == today: #防呆(當日是否領過)
        return jsonify({'status': 'error', 'message': '今天已經簽到過囉！'}), 400
    current_user.last_checkin = today
    current_user.coins = (current_user.coins or 0) + 50
    db.session.commit()
    return jsonify({'status': 'success', 'message': '簽到成功！獲得 50 錢錢 💰'})

@app.route('/daily_task', methods=['GET', 'POST'])
@app.route('/daily', methods=['GET', 'POST'])
@login_required
def daily_task():
    today_str = date.today().strftime('%Y-%m-%d') #取得今天日期的字串
    record = DailyRecord.query.filter_by(user_id=current_user.id, date=today_str).first()
    #資料庫歷史紀錄表看當日有沒有寫過日誌
    if request.method == 'POST':
        height_val = request.form.get('height')
        weight_val = request.form.get('weight')
        gender_val = request.form.get('gender')
        water_val = int(request.form.get('water', 0))
        steps_val = int(request.form.get('steps', 0))
        diary_val = request.form.get('diary', '').strip()
        
        #更新User模型的暫存狀態
        current_user.height = float(height_val) if height_val else None
        current_user.weight = float(weight_val) if weight_val else None
        current_user.gender = gender_val
        current_user.water = water_val
        current_user.steps = steps_val
        current_user.diary = diary_val
        
        #更新或新建DailyRecord資料庫紀錄
        if record:
            #如果今天已經有紀錄，就進行修改
            record.water = water_val
            record.steps = steps_val
            record.diary = diary_val
            flash("日誌修改成功！(今日已領過獎勵囉)", "info")
        else:
            #全新建立修正給予所有欄位數值
            record = DailyRecord()
            record.user_id = current_user.id
            record.date = today_str
            record.water = water_val
            record.steps = steps_val   #確保步數寫入
            record.diary = diary_val   #確保心情日記寫入
            
            db.session.add(record) #新增這筆歷史紀錄
            
            # 給予獎勵
            current_user.coins = (current_user.coins or 0) + 100
            flash("🎉 感謝認真記錄！100 金幣已成功撥入您的時空金庫！💰", "success")
            
        db.session.commit()
        return redirect('/lobby')   #存完檔後重新導向引導玩家回到大廳
        
    template_name = 'daily.html' if request.path == '/daily' else 'daily_task.html'
    return render_template(template_name, user=current_user, record=record)

@app.route('/get_health_record', methods=['GET'])
@login_required
def get_health_record():
    # 1. 從網址參數中取得日期字串 (例如: "2026-06-04")
    date_string = request.args.get('date')
    
    if not date_string:
        return jsonify({'status': 'error', 'message': '缺少日期參數'}), 400
        
    # 2. 去資料庫找出對應的歷史紀錄
    record = DailyRecord.query.filter_by(user_id=current_user.id, date=date_string).first()
    
    if record:
        # 🟢 完美契合前端 res.status === 'success' && res.found 結構
        return jsonify({
            'status': 'success',
            'found': True,
            'data': {
                'water': record.water if record.water is not None else 0,
                'steps': record.steps if record.steps is not None else 0,
                'diary': record.diary if record.diary else ""
            }
        })
    else:
        # 🟡 沒找到紀錄時的格式
        return jsonify({
            'status': 'success',
            'found': False,
            'data': {
                'water': 0,
                'steps': 0,
                'diary': ""
            }
        })

#運動軌跡地圖與步數同步核心路由
@app.route('/relief', methods=['GET'])
@login_required
def relief_page():
    """ 渲染帶有地圖運動軌跡計算頁面 """
    today_str = date.today().strftime('%Y-%m-%d')
    record = DailyRecord.query.filter_by(user_id=current_user.id, date=today_str).first()
    current_steps = record.steps if record else current_user.steps
    return render_template('relief.html', user=current_user, current_steps=current_steps)

@app.route('/api/update_steps', methods=['POST'])
@login_required
def update_steps():
    """ 接收前端地圖 GPS 計算出來的累計步數或步行距離變更，同步到資料庫 """
    data = request.get_json() or {}
    additional_steps = int(data.get('steps', 0))
    lat = data.get('lat') 
    lng = data.get('lng')

    if additional_steps <= 0:
        return jsonify({'success': False, 'message': '步數無實質增加'}), 400

    today_str = date.today().strftime('%Y-%m-%d')
    record = DailyRecord.query.filter_by(user_id=current_user.id, date=today_str).first()

    if not record:
        record = DailyRecord(user_id=current_user.id, date=today_str, water=current_user.water, steps=0)
        db.session.add(record)

    record.steps += additional_steps
    current_user.steps = record.steps
    
    bonus_coins = int(additional_steps / 100)
    if bonus_coins > 0:
        current_user.coins = (current_user.coins or 0) + bonus_coins

    db.session.commit()
    return jsonify({
        'success': True, 
        'total_steps': record.steps, 
        'earned_coins': bonus_coins,
        'message': f'成功同步！幫你增加了 {additional_steps} 步！'
    })


# =====================================================================
# 🔮 心理測驗系統 (🛠️ 已優化：動態讀取 questions.json + 隨機抽 10 題) 🔮
# =====================================================================

@app.route('/quiz', methods=['GET'])
@login_required
def quiz_page():
    # 🎯 棄用 app.root_path，改用當前檔案的絕對路徑定位，在 Render 容器最穩固
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, 'questions.json')
    
    # 🛡️ 安全防呆：如果找不到檔案，拋出提示
    if not os.path.exists(json_path):
        return f"錯誤：找不到題庫檔案，請確認 questions.json 是否在專案根目錄！(路徑: {json_path})", 404
        
    try:
        # 讀取外部的 JSON 題目庫
        with open(json_path, 'r', encoding='utf-8') as f:
            quiz_pool = json.load(f)
    except Exception as e:
        return f"錯誤：讀取 json 檔案失敗，請檢查格式是否正確。錯誤訊息: {str(e)}", 500

    # 隨機抽題機制（最多抽 10 題）
    num_to_select = min(len(quiz_pool), 10)
    selected_questions = random.sample(quiz_pool, num_to_select)
    
    # Session只儲存這批題目的「ID 清單」
    session['current_quiz_ids'] = [q['id'] for q in selected_questions]
    return render_template('quiz.html', questions=selected_questions)
@app.route('/quiz/submit', methods=['POST'])
@login_required
def quiz_submit():
    data = request.get_json() or {}
    user_answers = data.get('answers', {})

    current_quiz_ids = session.get('current_quiz_ids', [])
    if not current_quiz_ids:
        return jsonify({'success': False, 'message': '測驗過期或異常，請重新整理頁面。'}), 400

    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, 'questions.json')
    
    if not os.path.exists(json_path):
        return jsonify({'success': False, 'message': '伺服器錯誤：找不到題庫檔案。'}), 500
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            quiz_pool = json.load(f)
    except Exception as e:
        return jsonify({'success': False, 'message': f'題庫讀取失敗: {str(e)}'}), 500

    quiz_questions = [q for q in quiz_pool if q.get('id') in current_quiz_ids]

    # =====================================================================
    # 🎯 以下完全維持你原本精心設計的計分、情緒資料庫與發放金幣邏輯（一字不漏）
    # =====================================================================
    emotion_database = {
        "anxiety": {"name": "阿焦", "image": "anxiety.png", "title": "高焦慮狀態", "desc": "你最近內心似乎有些靜不下來，容易胡思亂想，未來的事情讓你有些擔憂。"},
        "depression": {"name": "憂憂", "image": "depression.png", "title": "情緒低落", "desc": "動力有些不足，內心感到疲憊與灰心，這時候適合好好休息、抱抱自己。"},
        "anger": {"name": "怒怒", "image": "anger.png", "title": "怒氣積壓", "desc": "最近有些事情讓你感到不公平或受挫，內心有一把無名火在燒。"},
        "envy": {"name": "阿慕", "image": "envy.png", "title": "羨慕酸楚", "desc": "看著別人的生活與成就，內心不自覺酸了一下，但這也是前進的動力。"},
        "joy": {"name": "樂樂", "image": "joy.png", "title": "喜悅滿足", "desc": "太棒了！你內心充滿正能量與快樂，目前的狀態非常理想，請繼續保持！"},
        "calm": {"name": "阿理", "image": "calm.png", "title": "非常理智", "desc": "你目前處於極為和諧、冷靜的狀態，能用超然且客觀的角度看待一切事物。"},
        "shy": {"name": "羞羞", "image": "shy.png", "title": "害羞敏感", "desc": "內心有些退縮與敏感，面對新環境或人群時感到一絲不自在，想回歸舒適圈。"},
        "Hate": {"name": "厭厭", "image": "Hate.png", "title": "傲嬌厭世", "desc": "現在感覺有點平等怨恨所有的一切，白眼翻到後腦勺，對什麼事情都提不起勁。"},
        "confused": {"name": "阿茫", "image": "confused.png", "title": "迷茫困惑", "desc": "站在十字路口，有些看不清未來的方向，腦袋一片混亂，需要靜心整理。"},
        "flat": {"name": "阿廢", "image": "flat.png", "title": "靈魂出竅", "desc": "持續低電量！沒有特別快樂，也沒有特別難過，內心毫無波瀾、只想原地躺平。"},
        "excited": {"name": "嗨嗨", "image": "excited.png", "title": "多巴胺爆發", "desc": "體內的多巴胺正在瘋狂分泌！你對某件事充滿了強烈的期待與極高的熱情！"}
    }

    alias_map = {
        "anxiety": "anxiety", "calm": "calm", "joy": "joy", "depression": "depression", "anger": "anger",
        "envy": "envy", "shy": "shy", "hate": "Hate", "Hate": "Hate", "confused": "confused", "flat": "flat", "excited": "excited"
    }

    # ☯️ 11種情緒完美相扣（互斥）矩陣
    conflict_map = {
        "calm": ["anger", "excited", "anxiety", "flat"],
        "joy": ["depression", "Hate"],
        "flat": ["excited", "calm"],
        "anxiety": ["calm"],
        "anger": ["calm"],
        "depression": ["joy", "excited"],
        "Hate": ["joy"],
        "excited": ["flat", "calm"]
    }

    # 給予每個維度隨機底分
    scores = {dim: random.uniform(1.0, 3.5) for dim in emotion_database.keys()}

    # 精準比對這一次抽出的題目與使用者的回答
    for q in quiz_questions:
        q_id_str = str(q.get('id'))
        if q_id_str in user_answers:
            choice_idx = int(user_answers[q_id_str])
            choices_list = q.get('choices', [])
            if choice_idx < len(choices_list):
                selected_choice = choices_list[choice_idx]
                val = int(selected_choice.get('value', 3))
                raw_dim = selected_choice.get('dimension')
                
                target_dim = alias_map.get(raw_dim)
                if target_dim and target_dim in scores:
                    # 1. 當前選中的情緒加分
                    scores[target_dim] += val
                    
                    # ⚖️ 2. 觸發相扣機制：扣除對立面情緒的分數 (每次扣除當前權重的 60%)
                    if target_dim in conflict_map:
                        for conflict_dim in conflict_map[target_dim]:
                            if conflict_dim in scores:
                                scores[conflict_dim] = max(0.0, scores[conflict_dim] - (val * 0.6))
                                
                else:
                    fallback_dims = list(emotion_database.keys())
                    mapped_dim = fallback_dims[(choice_idx + int(q_id_str or 0)) % len(fallback_dims)]
                    scores[mapped_dim] += (val + 2)
    all_emotions = []
    for dim, total_score in scores.items():
        calc_score = min(round(total_score + random.uniform(0.1, 0.8), 1), 10.0)
        all_emotions.append({
            "dim": dim,
            "name": emotion_database[dim]["name"],
            "image": emotion_database[dim]["image"], 
            "title": emotion_database[dim]["title"],
            "score": calc_score,
            "desc": emotion_database[dim]["desc"]
        })

    all_emotions = sorted(all_emotions, key=lambda x: x['score'], reverse=True)
    top_emotion = all_emotions[0]

    filtered_emotions = []
    if len(all_emotions) <= 5:
        filtered_emotions = all_emotions
    else:
        filtered_emotions = all_emotions[:4]
        fifth_score = all_emotions[3]['score'] if len(filtered_emotions) >= 4 else 0
        if len(all_emotions) >= 5:
            fifth_score = all_emotions[4]['score']
            
        for emo in all_emotions[4:]:
            if emo['score'] >= fifth_score:
                filtered_emotions.append(emo)
            else:
                break

    today_str = datetime.now().strftime('%Y-%m-%d')
    record = DailyRecord.query.filter_by(user_id=current_user.id, date=today_str).first()
    
    water = record.water if record else 0
    steps = record.steps if record else 0
    advice_list = []
    
    if water < 1500:
        advice_list.append(f"今日喝水量僅 {water}ml。多喝水能穩定緊繃的神經系統！")
    else:
        advice_list.append(f"今日喝水量達到 {water}ml！水份補充得非常完美。")
        
    if steps < 5000:
        advice_list.append(f"今日累計 {steps} 步。等等不妨出門走走散散步、轉換心情！")
    else:
        advice_list.append(f"今日散步 {steps} 步，身體活動量相當達標！")
        
    has_bad_vibe = top_emotion['dim'] in ["anxiety", "depression", "anger", "Hate", "confused"]
    if has_bad_vibe:
        summary_text = f"綜合身心點評：今日你的心靈雷達偵測到主導情緒為【{top_emotion['name']}】。內心承受著些許波動，請給自己一個深呼吸的空間。"
    else:
        summary_text = f"綜合身心點評：你今天的能量場由【{top_emotion['name']}】主導，目前的狀態非常和諧穩定，是個安頓身心的好日子！"

    current_user.coins = (current_user.coins or 0) + 50
    db.session.commit()

    return jsonify({
        'success': True,
        'top_emotion': top_emotion,
        'all_emotions': filtered_emotions,
        'report': {
            "water": water,
            "steps": steps,
            "advice": advice_list,
            "summary": summary_text,
            "has_diary": "已填寫" if (record and record.diary and record.diary.strip()) else "未填寫"
        }
    })


# =====================================================================
# 🚀 全新新增：何倫碼（RIASEC）職涯發展適配度測驗路由 (完全獨立，不影響原本 quiz)
# =====================================================================

@app.route('/h', methods=['GET'])
def holland_page():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, 'H.json')

    if not os.path.exists(json_path):
        return f"【何倫碼錯誤】找不到題庫檔案，請確認 H.json 是否放在：{json_path}", 404

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            holland_pool = json.load(f)

        # 建立題目 ID Session
        session['holland_quiz_ids'] = [
            q.get('id')
            for q in holland_pool
            if q.get('id') is not None
        ]

        print("已建立 holland_quiz_ids:", session['holland_quiz_ids'])

        return render_template(
            'h.html',
            questions=holland_pool
        )

    except Exception as e:
        return f"【何倫碼錯誤】讀取檔案或渲染失敗，詳細原因: {str(e)}", 500


@app.route('/h/submit', methods=['POST'])
@login_required
def holland_submit():

    data = request.get_json() or {}
    user_answers = data.get('answers', {}) 
    print("收到資料:", data)

    print("Session內容:", dict(session))

    holland_quiz_ids = session.get('holland_quiz_ids', [])

    print("holland_quiz_ids:", holland_quiz_ids)

    if not holland_quiz_ids:
        return jsonify({'success': False, 'message': '測驗過期或異常，請重新整理頁面。'}), 400

    # 🎯 定位當前檔案的絕對路徑
    base_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(base_dir, 'H.json')
    
    if not os.path.exists(json_path):
        return jsonify({'success': False, 'message': '伺服器錯誤：找不到題庫檔案 H.json。'}), 500
        
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            quiz_pool = json.load(f)
    except Exception as e:
        return jsonify({'success': False, 'message': f'題庫讀取失敗: {str(e)}'}), 500

    # 精準過濾出這一次前端渲染給使用者的何倫碼題目
    quiz_questions = [q for q in quiz_pool if q.get('id') in holland_quiz_ids]

    # 🎯 何倫碼（RIASEC）職業理論資料庫與核心矩陣
    holland_database = {
        "R": {
            "name": "實作型 (Realistic)", 
            "title": "務實動手做", 
            "desc": "你偏好具體、需要親自操作的工作環境。喜歡與機械、工具、動植物等具體實物打交道，通常個性務實、踏實，比起抽象的社交或純理論，更享受產出實體成果的過程。"
        },
        "I": {
            "name": "研究型 (Investigative)", 
            "title": "思考與分析", 
            "desc": "你充滿強烈的好奇心與求知慾。面對未解之謎或複雜數據時，習慣進行嚴謹的邏輯推理、觀察與科學研究。比起團隊社交，你更享受獨立思考與拆解問題背後的底層規律。"
        },
        "A": {
            "name": "藝術型 (Artistic)", 
            "title": "創意與直覺", 
            "desc": "你追求自由、美感與自我表達。天生擁有敏銳的直覺與創造力，極度討厭死板的規則與一成不變的公式。習慣透過文字、色彩或音樂抒發情感，喜歡打破常規的工作型態。"
        },
        "S": {
            "name": "社交型 (Social)", 
            "title": "熱心助人", 
            "desc": "你具有強大的同理心與情感包容力。非常熱衷於與人互動，擅長傾聽、溝通、開導或培育他人。對你來說，能夠實質幫助到人、療癒他人或傳授知識，比面對冷冰冰的數據更有價值。"
        },
        "E": {
            "name": "企業型 (Enterprising)", 
            "title": "領導與影響", 
            "desc": "你精力充沛、具有冒險精神且說服力極強。在團隊中總是能敏銳察覺商業機會，熱衷於站在最前線主導大局、爭取資源並帶領團隊。追求高度的成就感、社會地位與實質回報。"
        },
        "C": {
            "name": "常規型 (Conventional)", 
            "title": "井然有序", 
            "desc": "你是組織中不可或缺的細節守護者。在有明確SOP（標準作業程序）、條理分明且注重規範的環境中表現最為出色。擅長處理文書、檔案與精準數據，做事情一絲不苟、效率極高。"
        }
    }

    # ☯️ 何倫碼六角形（RIASEC）對角互斥衝突矩陣
    conflict_map = {
        "R": ["S"], "I": ["E"], "A": ["C"],
        "S": ["R"], "E": ["I"], "C": ["A"]
    }

    # 給予每個維度隨機底分
    scores = {dim: random.uniform(1.0, 2.0) for dim in holland_database.keys()}

    # 計算使用者回答的實際權重
    for q in quiz_questions:
        q_id_str = str(q.get('id'))
        if q_id_str in user_answers:
            choice_idx = int(user_answers[q_id_str])
            choices_list = q.get('choices', [])
            
            if choice_idx < len(choices_list):
                selected_choice = choices_list[choice_idx]
                val = int(selected_choice.get('value', 3))      # 分數權重
                raw_dim = selected_choice.get('type')           # 取得 R/I/A/S/E/C
                
                if raw_dim:
                    target_dim = raw_dim.upper()
                    if target_dim in scores:
                        # 1. 該興趣維度加分
                        scores[target_dim] += val
                        
                        # ⚖️ 2. 觸發對角互斥機制：扣除相對立興趣維度的分數（每次扣除當前權重的 50%）
                        if target_dim in conflict_map:
                            for conflict_dim in conflict_map[target_dim]:
                                if conflict_dim in scores:
                                    scores[conflict_dim] = max(0.0, scores[conflict_dim] - (val * 0.5))
            else:
                fallback_dims = list(holland_database.keys())
                mapped_dim = fallback_dims[(choice_idx + int(q_id_str or 0)) % len(fallback_dims)]
                scores[mapped_dim] += 2

    # 包裝所有類型的總得分
    all_types = []
    for dim, total_score in scores.items():
        calc_score = min(round(total_score + random.uniform(0.1, 0.5), 1), 10.0)
        all_types.append({
            "type": dim,
            "name": holland_database[dim]["name"],
            "title": holland_database[dim]["title"],
            "score": calc_score,
            "percent": int(calc_score * 10), # 給前端進度條百分比
            "desc": holland_database[dim]["desc"]
        })

    # 由高到低排序，算出你的何倫碼
    all_types = sorted(all_types, key=lambda x: x['score'], reverse=True)
    
    # 取出前三名的高分字母組合
    holland_code = "".join([item['type'] for item in all_types[:3]])
    top_type = all_types[0]

    # 🚀 動態生成何倫三碼組合職業建議
    primary_two = holland_code[:2]
    job_recommendations = {
        "RI": ["🔧 自動化機器人研外工程師", "🧬 醫療器材精密製造師", "⚙️ 科技廠高階設備維修工程師"],
        "RC": ["📊 數據中心機房運維精算師", "📑 土木營建品質與安檢稽核員", "💻 全棧系統後端工程師"],
        "RA": ["🎨 3D 動畫與遊戲物理引擎設計師", "📐 工業產品外觀與結構設計師", "🎬 影視特效實體模型道具師"],
        "IR": ["🧪 生物醫學核心實驗室研究員", "💻 AI 演算法與深度學習科學家", "🔬 數據挖掘與統計分析專家"],
        "IA": ["💡 新興產品互動設計專家 (UX Researcher)", "📊 趨勢與科幻文學自由作家", "🧩 密室逃脫與策略遊戲關卡設計師"],
        "IS": ["🩺 臨床精神科醫師 / 心理醫學研究員", "🏫 大學理工與科學領域教授", "🌱 公共衛生與流行病防治專家"],
        "AI": ["💡 設計思考 (Design Thinking) 顧問", "🎨 數位多媒體藝術總監", "💻 網頁前端視覺架構師"],
        "AS": ["🎭 專業心理劇舞台引導師", "✍️ 生涯諮詢專欄作家", "🎨 兒童藝術治療與潛能開發師"],
        "AE": ["📈 廣告創意總監 / 行銷企劃教父", "🚀 新創產品 brand 包裝與主理人", "📢 跨國公關與社群意見領袖"],
        "SI": ["🎓 學校職涯輔導特聘心理諮商師", "🩹 臨床職能 / 物理治療師", "🏢 企業員工心理諮商特助 (EAP)"],
        "SA": ["🤝 非營利組織 (NGO) 創意專案發起人", "🏫 藝術與人史跨領域教師", "🌱 團隊凝聚力情緒工作坊引導師"],
        "SE": ["💼 企業人力資源發展經理 (HRD)", "🤝 高階客戶關係維護 (CRM) 專家", "🎤 跨國論壇專業主持人 / 專案經理"],
        "ES": ["🚀 創業家 / 新創公司共同創辦人", "📈 連鎖品牌市場策略開發總監", "💼 公關經理與大客戶開發代表"],
        "EA": ["📢 數位行銷與爆款活動策劃主管", "💎 時尚與奢侈品市場開發經理", "🎬 獨立製片人 / 傳媒公司主理人"],
        "EC": ["📊 投資銀行分析師 (Venture Capital)", "💼 企業特助 / 營運流程效率優化主管", "📈 電商平台專案控管經理 (PM)"],
        "CE": ["📑 國際會計師事務所高級審計師", "📊 風險控管與法務合規部主管", "💻 資料庫管理與資安系統防護專家"],
        "CS": ["🏢 政府機關行政決策與內部培訓官", "📊 醫療機構病歷資料庫控管主管", "📑 大型企業總務與採購供應鏈經理"],
        "CI": ["🎯 保險精算師 / 特級金融分析師", "📑 國家專利技術與智慧財產權審查員", "📊 品質工程 (QE) 與可靠度分析師"]
    }
    
    recommended_jobs = job_recommendations.get(primary_two, job_recommendations.get(primary_two[::-1], [
        f"💼 符合 {holland_code} 導向的綜合策略顧問",
        f"📊 跨領域專案經理 (Project Manager)",
        f"🚀 企業組織架構優化與發展規劃師"
    ]))

    # 📋 結合 DailyRecord 生理日誌交叉比對
    today_str = datetime.now().strftime('%Y-%m-%d')
    record = DailyRecord.query.filter_by(user_id=current_user.id, date=today_str).first()
    
    water = record.water if record else 0
    steps = record.steps if record else 0
    advice_list = []
    
    if water < 1500:
        advice_list.append(f"💧 今日喝水量僅 {water}ml。多喝水能保持大腦思緒清晰、維持高水準專注力！")
    else:
        advice_list.append(f"💧 今日喝水量達到 {water}ml！身體水分極佳，思維運作非常流暢。")
        
    if steps < 5000:
        advice_list.append(f"🏃 今日累計 {steps} 步。不妨起立走走，活動身體有助於激發新的職涯靈感！")
    else:
        advice_list.append(f"🏃 今日散步 {steps} 步，身體多巴胺與代謝指數相當達標！")

    summary_text = (
        f"職涯星圖點評：經過交叉分析，您的核心何倫密碼為【{holland_code}】，目前在【{top_type['title']}】展現出最強烈的潛能。 "
        f"這代表您是一個具備{top_type['title']}特質的人，當您身處在符合此密碼的環境中，最容易獲得工作快樂與成就感！"
    )

    # 發放 50 枚金幣獎勵
    current_user.coins = (current_user.coins or 0) + 50
    db.session.commit()

    return jsonify({
        'success': True,
        'sorted_types': all_types,
        'report': {
            "holland_code": holland_code,
            "water": water,
            "steps": steps,
            "advice": advice_list,
            "summary": summary_text,
            "jobs": recommended_jobs,
            "has_diary": "已填寫" if (record and record.diary and record.diary.strip()) else "未填寫"
        }
    })

# =====================================================================
# 🧠 全新新增：MBTI 16型高階人格特質測驗路由 (完全獨立，不影響其他測驗)
# =====================================================================

@app.route('/m', methods=['GET'])
@login_required  # 🎯 補上這行，確保登入狀態與 session 勾稽完全正常！
def mbti_page():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'M.json') # 56題庫檔案
        
        if not os.path.exists(json_path):
            return f"【MBTI錯誤】找不到題庫檔案，請確認 M.json 是否放在：{json_path}", 404
            
        with open(json_path, 'r', encoding='utf-8') as f:
            mbti_pool = json.load(f)
            
        # 鎖定當前題目的 ID
        session['mbti_quiz_ids'] = [q['id'] for q in mbti_pool]
        
        # 🎯 注意：這裡渲染的檔名一定要跟 templates 資料夾下的一模一樣
        return render_template('m.html', questions=mbti_pool)
    except Exception as e:
        return f"【MBTI錯誤】讀取檔案或渲染失敗，詳細原因: {str(e)}", 500


@app.route('/m/submit', methods=['POST'])
@login_required
def mbti_submit():
    try:
        from datetime import datetime
        
        data = request.get_json() or {}
        user_answers = data.get('answers', {})  
        
        mbti_quiz_ids = session.get('mbti_quiz_ids', [])
        if not mbti_quiz_ids:
            # 如果 session 遺失，我們自動幫他重新載入，不讓他報錯
            pass

        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'M.json')
        
        if not os.path.exists(json_path):
            return jsonify({'success': False, 'message': '伺服器錯誤：找不到題庫檔案 M.json。'}), 500
            
        with open(json_path, 'r', encoding='utf-8') as f:
            mbti_pool = json.load(f)

        # =====================================================================
        # 📊 MBTI 核心五點量表算分引擎
        # =====================================================================
        dimensions = {
            "EI": {"E": 0, "I": 0},
            "SN": {"S": 0, "N": 0},
            "TF": {"T": 0, "F": 0},
            "JP": {"J": 0, "P": 0}
        }

        weight_map = {
            0: {"same": 2, "opposite": 0},  
            1: {"same": 1, "opposite": 0},  
            2: {"same": 0, "opposite": 0},  
            3: {"same": 0, "opposite": 1},  
            4: {"same": 0, "opposite": 2}   
        }

        opposite_letter = {
            "E": "I", "I": "E",
            "S": "N", "N": "S",
            "T": "F", "F": "T",
            "J": "P", "P": "J"
        }

        for q in mbti_pool:
            q_id_str = str(q['id'])
            dim_key = q['dimension']  
            direction = q['direction'] 
            
            if q_id_str in user_answers:
                choice_idx = int(user_answers[q_id_str])  
                if choice_idx in weight_map:
                    weights = weight_map[choice_idx]
                    opp = opposite_letter[direction]
                    
                    dimensions[dim_key][direction] += weights["same"]
                    dimensions[dim_key][opp] += weights["opposite"]

        # =====================================================================
        # 🔮 判定 16 型人格代碼與百分比計算
        # =====================================================================
        mbti_code = ""
        chart_data = {}  

        # 1. E vs I
        e_score = dimensions["EI"]["E"]
        i_score = dimensions["EI"]["I"]
        total_ei = e_score + i_score if (e_score + i_score) > 0 else 1
        if e_score >= i_score:
            mbti_code += "E"
            chart_data["EI"] = {"lead": "E", "name": "外向型", "percent": int((e_score / total_ei) * 100)}
        else:
            mbti_code += "I"
            chart_data["EI"] = {"lead": "I", "name": "內向型", "percent": int((i_score / total_ei) * 100)}

        # 2. S vs N
        s_score = dimensions["SN"]["S"]
        n_score = dimensions["SN"]["N"]
        total_sn = s_score + n_score if (s_score + n_score) > 0 else 1
        if s_score >= n_score:
            mbti_code += "S"
            chart_data["SN"] = {"lead": "S", "name": "實感型", "percent": int((s_score / total_sn) * 100)}
        else:
            mbti_code += "N"
            chart_data["SN"] = {"lead": "N", "name": "直覺型", "percent": int((n_score / total_sn) * 100)}

        # 3. T vs F
        t_score = dimensions["TF"]["T"]
        f_score = dimensions["TF"]["F"]
        total_tf = t_score + f_score if (t_score + f_score) > 0 else 1
        if t_score >= f_score:
            mbti_code += "T"
            chart_data["TF"] = {"lead": "T", "name": "思考型", "percent": int((t_score / total_tf) * 100)}
        else:
            mbti_code += "F"
            chart_data["TF"] = {"lead": "F", "name": "情感型", "percent": int((f_score / total_tf) * 100)}

        # 4. J vs P
        j_score = dimensions["JP"]["J"]
        p_score = dimensions["JP"]["P"]
        total_jp = j_score + p_score if (j_score + p_score) > 0 else 1
        if j_score >= p_score:
            mbti_code += "J"
            chart_data["JP"] = {"lead": "J", "name": "判斷型", "percent": int((j_score / total_jp) * 100)}
        else:
            mbti_code += "P"
            chart_data["JP"] = {"lead": "P", "name": "感知型", "percent": int((p_score / total_jp) * 100)}

        # 👑 16 型人格龐大資料庫核心
        mbti_database = {
            "INTJ": {"title": "建築師 ", "alias": "戰略大師", "desc": "你站在思想的制高點，擁有極其嚴密的邏輯與宏大的眼界。", "jobs": [" AI 系統首席架構師", " 對沖基金量化策略師"]},
            "INTP": {"title": "邏輯學家 ", "alias": "瘋狂科學家", "desc": "你是天生的思想家與解謎者。對你來說，生命是一場永無止境的思維實驗。", "jobs": [" 區塊鏈核心演算法工程師", " 量子物理研究員"]},
            "ENTJ": {"title": "指揮官 ", "alias": "鐵血領袖", "desc": "天生的開拓者與大局掌控者。你體內流淌著追求效率與勝利的血液。", "jobs": [" 新創科技公司執行長 (CEO)", " 風險投資機構合夥人"]},
            "ENTP": {"title": "辯論家 ", "alias": "顛覆性發明家", "desc": "你是思維的魔術師，熱衷於打破常規、挑戰權威。", "jobs": [" 增長駭客與創新產品主理人", " 商業奇襲廣告策略總監"]},
            "INFJ": {"title": "提倡者 ", "alias": "心靈先知", "desc": "16型人格中最稀有的存在。你外表溫和安靜，內心卻激盪著深邃的理想主義。", "jobs": [" 高階深度心理諮商專家", " 跨領域生命哲學特聘教授"]},
            "INFP": {"title": "調停者 ", "alias": "靈魂藝術家", "desc": "你是無可救藥的浪漫主義者，內心擁有一座無比絢麗的精神花園。", "jobs": [" 獨立原創繪本藝術家", " 敘事治療引導師"]},
            "ENFJ": {"title": "主人公 ", "alias": "精神領袖", "desc": "你散發著耀眼的人格魅力與感召力。你天生具備強大的利他主義。", "jobs": [" 企業文化發展副總", " 跨國論壇專業首席主持人"]},
            "ENFP": {"title": "競選者 ", "alias": "快樂感染源", "desc": "你是自由而自由奔放的靈魂，生命對你而言是一場充滿驚喜的冒險。", "jobs": [" 爆款活動策劃與新媒體總監", " 設計思考引導導師"]},
            "ISTJ": {"title": "物流師 ", "alias": "帝國守護者", "desc": "你是社會和組織中穩固的中流柱。責任感、忠誠與精準是你的代名詞。", "jobs": [" 國際資深審計師", " 國家級資安系統防護專家"]},
            "ISFJ": {"title": "守衛者 ", "alias": "幕後守護天使", "desc": "你擁有無比溫暖、體貼且低調的人格特質。你總是在背後默默付出。", "jobs": [" 臨床高級照護師", " 頂級企業員工福祉經經理"]},
            "ESTJ": {"title": "總經理 ", "alias": "秩序建構者", "desc": "你是天生的執行官與規範維護者。你堅信事實、注重結果。", "jobs": [" 跨國製造業營運總監 (COO)", " 法律合規審查官"]},
            "ESFJ": {"title": "執政官 ", "alias": "頂級社交家", "desc": "你是社交圈中的熱心大姐頭。你極度在乎人際網絡的社交和諧。", "jobs": [" 高階客戶關係維護總監", " 連鎖教育機構培訓導師"]},
            "ISTP": {"title": "鑑賞家 ", "alias": "機械與代碼黑客", "desc": "你是一個特立獨行的實踐者。心思沉穩冷計，對工具操作擁有驚人天賦。", "jobs": [" 全棧後端與底層黑客工程師", " 自動化機器人精密製造員"]},
            "ISFP": {"title": "探險家 ", "alias": "美學實踐者", "desc": "你是安靜、溫和且活在當下的藝術靈魂。你擁有敏銳的感官與獨特美學。", "jobs": [" 高級工業設計師", " 數位多媒體視覺美術師"]},
            "ESTP": {"title": "企業家 ", "alias": "極限衝鋒手", "desc": "你是行動力爆表的代名詞。思維敏捷、精力充沛，對機會有著野獸直覺。", "jobs": [" 創業家 / 新創拓荒經理", "連鎖品牌市場開拓主管"]},
            "ESFP": {"title": "表演者 ", "alias": "人間開心果", "desc": "你是行走的聚光燈，哪裡有你，哪裡就有笑聲與掌聲。", "jobs": [" 演藝娛樂全職演員 / 網紅", " 時尚潮流品牌視覺行銷主主理人"]}
        }

        result_meta = mbti_database.get(mbti_code, {
            "title": "神祕探險家 ", "alias": "潛能待覺醒", "desc": "您的人格編碼展現出了高度多元特質。", "jobs": [" 跨領域綜合策略顧問"]
        })

        # 📋 這裡是最關鍵的修正：絕對要把 advice_list 塞入預設文字，不讓前端抓空！
        advice_list = [
            f"【MBTI心靈防禦】身為核心特質為 {mbti_code} 的 {result_meta['title']}，請保持平衡的身心能量。",
            "【跨界日常建議】建議您今日補足 2000cc 飲水量，並維持規律的步伐以釋放潛在壓力。"
        ]
        
        summary_text = (
            f"診斷：確認您的核心人格特質為【{mbti_code}】也就是【{result_meta['title']} — {result_meta['alias']}】。 "
            f"置身於高契合度的環境中，最容易爆發出驚人的職業成就感！"
        )

        # 🎯 用最高等級的安全 Try-Catch 包裹資料庫寫入，就算金幣功能爆掉，也要讓算分成功回傳！
        try:
            current_user.coins = (current_user.coins or 0) + 50
            db.session.commit()
            has_diary_status = "已填寫"
        except:
            db.session.rollback()
            has_diary_status = "未填寫"

        # 🎯 完美回傳完整的 report 結構，前端 JavaScript 絕對能開開心心讀取完畢
        return jsonify({
            'success': True,
            'mbti_code': mbti_code,
            'chart_data': chart_data,
            'meta': result_meta,
            'report': {
                'advice': advice_list,
                'summary': summary_text,
                'has_diary': has_diary_status
            }
        })
    except Exception as e:
        # 如果中間有任何意外，直接印出錯誤訊息，不讓前端卡在「量子矩陣精算中...」
        return jsonify({'success': False, 'message': f'後端算分引擎意外崩潰: {str(e)}'}), 500
# ==========================================
# 🧭 4. 五大性格特質 (Big Five) 雙軌路由
# ==========================================

@app.route('/o', methods=['GET'])
def ocean_page():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'O.json')
        
        # 1. 自動偵測檔案是否存在
        if not os.path.exists(json_path):
            return f"【路徑偵測失敗】找不到題庫檔案 O.json！請確認它是否放在這裡：{json_path}", 500
            
        with open(json_path, 'r', encoding='utf-8') as f:
            ocean_pool = json.load(f)
            
        # 2. 渲染前端檔案
        return render_template('o.html', questions=ocean_pool)
        
    except Exception as e:
        # 如果程式碼內部有任何不為人知的錯誤，直接在網頁上噴出來給你看
        return f"【後端執行崩潰】進入 /o 路由時發生錯誤: {str(e)}", 500


@app.route('/o/submit', methods=['POST'])
def ocean_submit():
    try:
        data = request.get_json() or {}
        user_answers = data.get('answers', {})
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'O.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            ocean_pool = json.load(f)
            
        raw_scores = {"O": 0, "C": 0, "E": 0, "A": 0, "N": 0}
        max_score_per_dim = 16
        
        for q in ocean_pool:
            qid_str = str(q['id'])
            if qid_str in user_answers:
                val = int(user_answers[qid_str])
                if q['type'] == 'positive':
                    score = 4 - val
                else:
                    score = val
                raw_scores[q['dimension']] += score

        final_percentages = {}
        for dim, score in raw_scores.items():
            pct = round((score / max_score_per_dim) * 100)
            final_percentages[dim] = max(0, min(100, pct))

        # 這裡先給予安全預設值，避免撈取 session 健康數據時報錯
        water = session.get('today_water', 1200)
        steps = session.get('today_steps', 4500)
        
        advice_list = []
        if final_percentages['N'] >= 65:
            advice_list.append(f"【高情緒】您的心靈觸角極其敏銳，目前神經質指數達 {final_percentages['N']}%。建議今晚將散步步數提升至 8000 步。")
        else:
            advice_list.append(f"【情緒狀態】您的心理韌性極佳，情緒穩定度得分高。")
            
        if final_percentages['C'] >= 70:
            advice_list.append(f"【嚴謹自律反饋】強大的自律矩陣！您目前的嚴謹性得分高達 {final_percentages['C']}%。")
        else:
            advice_list.append(f"【提醒】您的嚴謹性得分較低，性格更傾向隨遇而安。")

        summary = f"您的五大特質雷達解碼完成：開放性 {final_percentages['O']}%、嚴謹性 {final_percentages['C']}%、外向性 {final_percentages['E']}%、親和性 {final_percentages['A']}%、神經質 {final_percentages['N']}%。"

        return jsonify({
            'success': True,
            'percentages': final_percentages,
            'advice': advice_list,
            'summary': summary
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'後端算分引擎崩潰: {str(e)}'}), 500
# =====================================================================
# ---------------- 🔮 塔羅牌系統 (防呆預設與死圖修復) ------------------
# =====================================================================

@app.route('/tarot')
@app.route('/tarot_page')
@login_required
def tarot_page():
    tarot_cards = [
        {"name": "高塔 (The Tower)", "image": "tower.png", "fallback": "https://placehold.co/150x240/2e1a47/ffffff?text=The+Tower"},
        {"name": "命運之輪 (Wheel of Fortune)", "image": "wheel.png", "fallback": "https://placehold.co/150x240/2e1a47/ffffff?text=Wheel+Of+Fortune"},
        {"name": "愚者 (The Fool)", "image": "fool.png", "fallback": "https://placehold.co/150x240/2e1a47/ffffff?text=The+Fool"}
    ]
    chosen_cards = random.sample(tarot_cards, 3) if len(tarot_cards) >= 3 else tarot_cards
    return render_template('tarot.html', cards=chosen_cards)

@app.route('/tarot', methods=['GET', 'POST'])
@login_required
def tarot():
    # 🔮 1. 建立 22 張大阿爾克那全套萬用牌義辭典（包含過去、現在、未來的專屬感受）
    tarot_dictionary = {
        "愚者": {"past": "前陣子經歷了一個充滿未知但勇敢的全新起點。", "present": "當下正面臨選擇，需要保持純真、不畏懼地去冒險。", "future": "未來將迎來一段自由、不受束縛的精彩新旅程。"},
        "魔術師": {"past": "前陣子主動運用才華開創了新局，掌握了主導權。", "present": "當下萬事俱備，妳擁有足夠的資源與能力去實踐計畫。", "future": "將會展現極強的創造力，事情能透過智慧迎刃而解。"},
        "女祭司": {"past": "過去一段時間妳比較被動，內心累積了許多直覺與智慧。", "present": "當下需要靜下心來聆聽內心的聲音，保持冷靜與觀察。", "future": "未來將會看清隱藏的真相，內心獲得平靜與智慧的昇華。"},
        "皇后": {"past": "前陣子經歷了一段生活富足、情感豐收的安穩時期。", "present": "當下充滿了愛與創造力，適合享受生活或滋養新計畫。", "future": "事情將迎來圓滿的轉機，生活中將充滿物質與精神的豐收。"},
        "皇帝": {"past": "過去妳試圖建立秩序，承擔了較多控管或管理責任。", "present": "當下需要展現決斷力與領導力，理性地去架構妳的生活。", "future": "將獲得高度的掌控權與穩定發展，建立起屬於妳的王國。"},
        "教皇": {"past": "前陣子可能得到了長輩、導師或傳統體制的協助與指引。", "present": "當下正在尋求內心的信仰、和諧，或是有學習、諮詢的需求。", "future": "未來會遇到命中注定的貴人相助，或是獲得智慧上的啟發。"},
        "戀人": {"past": "過去面臨過重要的人際結合、情感關係或關鍵的二選一抉擇。", "present": "當下正在享受美好的人際互動，或是需要跟隨真心做出決定。", "future": "未來將迎來和諧幸福的關係，不論是情感或合作都相當圓滿。"},
        "戰車": {"past": "前陣子妳充滿衝勁，為了目標克服困難、奮力前行。", "present": "當下正處於關鍵的衝刺期，需要堅強的意志力來掌控失衡的局面。", "future": "只要堅持下去，妳將憑藉強大的意志力突破重圍，獲得勝利。"},
        "力量": {"past": "過去妳學會了用溫柔克服剛強，用內心的韌性化解危機。", "present": "當下正面臨考驗，需要用耐心、勇氣與柔性的力量去包容與面對。", "future": "妳將成功馴服眼前的困難，內心會變得更加強大與自信。"},
        "隱者": {"past": "前陣子妳經歷了一段低調、向內探索或孤獨思考的沉澱期。", "present": "當下需要暫時退一步，獨立思考，從中尋找屬於妳的智慧之光。", "future": "將找到真正適合自己的核心答案，不再盲目跟隨外界。"},
        "命運之輪": {"past": "前陣子生活出現了預期之外的轉變，命運推了妳一把。", "present": "當下正站在順應局勢的交叉口，好運與改變的齒輪正在轉動。", "future": "轉機將至，命運會把妳帶往更有利、更順遂的全新階段。"},
        "正義": {"past": "前陣子經歷了一段心境轉換，正在為某事尋求公平合理的結論。", "present": "當下需要秉持理智、客觀的態度，做出誠實且權衡利弊的決定。", "future": "付出將得到應有的回報，事情會以最公平、客觀的方式圓滿落幕。"},
        "吊人": {"past": "過去一段時間妳做出了犧牲，或處於一種進退兩難的停滯狀態。", "present": "當下需要換個角度思考，換個心態面對眼前的卡關，以退為進。", "future": "這段沉澱與奉獻將換來極大的精神覺醒，看見完全不同的新曙光。"},
        "死神": {"past": "前陣子某個階段、關係或舊習慣已經徹底結束，經歷了斷捨離。", "present": "當下正處於破壞後的重組期，雖然有些不捨，但這必須發生。", "future": "置之死地而後生，舊的消失意味著更棒的新生與蛻變即將到來。"},
        "節制": {"past": "過去一段時間妳在不同的立場或情感中，努力進行協調與淨化。", "present": "當下正處於一種動態平衡中，需要好好調和、溝通，融合不同元素。", "future": "身心靈將達到完美的平衡，人際溝通、跨界合作都會極度順暢。"},
        "惡魔": {"past": "前陣子可能陷入了某些慾望、物質誘惑或不健康關係的束縛中。", "present": "當下正面臨某種執著或盲點，需要注意自己是否被負面情緒綁架。", "future": "只要看清這份執念的來源，妳就能打破沉迷，重新奪回掌控權。"},
        "高塔": {"past": "前陣子經歷了突如其來的衝擊或舊觀念的崩解，震驚了妳的內心。", "present": "當下正面臨突發的壓力或環境劇變，需要徹底打破原有的舒適圈。", "future": "雖然過程劇烈，但廢墟中會建立起更堅固、更真實的全新地基。"},
        "星星": {"past": "在經歷風雨過後，前陣子妳內心重新點燃了希望與療癒的火苗。", "present": "當下充滿著平靜與靈感，事情正朝著樂觀且充滿希望的方向發展。", "future": "願望將有機會達成，心靈獲得洗滌，未來前途一片光明燦爛。"},
        "月亮": {"past": "前陣子內心充滿了迷茫、不安與隱隱約約的恐懼，看不清方向。", "present": "當下周遭局勢曖昧不明，內心焦慮較重，容易被潛意識的直覺干擾。", "future": "迷霧終將散去，只要勇敢面對心中的恐懼，不確定性很快會澄清。"},
        "太陽": {"past": "前陣子妳的生活充滿了陽光、活力以及眾人的肯定，非常耀眼。", "present": "當下正處於極度幸運、充滿生命力且萬事順遂的黃金時刻。", "future": "未來將迎來完全的成功、幸福與滿滿的正能量，所有的努力都將發光！"},
        "審判": {"past": "前陣子妳聽到了內心的召喚，對過去的行為進行了深刻的反省。", "present": "當下正迎來一個重大的轉捩點，是做出關鍵抉擇、重獲新生的時刻。", "future": "沉冤得雪、沉睡的潛能被喚醒，妳即將迎來關鍵性的重大成功與復活。"},
        "世界": {"past": "前陣子某個大型計畫、關係或人生階段得到了完美的完結與成功。", "present": "當下感到十分和諧、功德圓滿，各方面都達到了理想的狀態。", "future": "事情將迎來真正最完美的終極圓滿，妳將踏入生命中最輝煌的新境界。"}
    }

    if request.method == 'POST':
        # 🎲 2. 隨機抽出 3 張不一樣的牌
        cards_pool = list(tarot_dictionary.keys())
        chosen = random.sample(cards_pool, 3)
        
        card_past = chosen[0]
        card_present = chosen[1]
        card_future = chosen[2]
        
        # ✍️ 3. 【黃金修正】去辭典抓取這三張牌「對應位置」的獨一無二解牌文字！
        analysis = (
            f"🔮【AI 占卜解析】\n\n"
            f"【過去：{card_past}】{tarot_dictionary[card_past]['past']}\n\n"
            f"【現在：{card_present}】{tarot_dictionary[card_present]['present']}\n\n"
            f"【未來：{card_future}】{tarot_dictionary[card_future]['future']}"
        )
        
        # 🚀 4. 將真正隨機且對齊的解析傳給前端
        return jsonify({"success": True, "cards": chosen, "analysis": analysis})
        
    return render_template('tarot.html')
# =====================================================================
# ---------------------- 🎮 節奏派對獨立路由系統 ----------------------
# =====================================================================

@app.route('/game', methods=['GET'])
@login_required
def game_page():
    return render_template('game.html', user=current_user)

@app.route('/game/pay', methods=['POST'])
@login_required
def game_pay():
    if current_user.coins >= 50:
        current_user.coins -= 50
        db.session.commit()
        return jsonify({"success": True, "msg": "投幣成功！開啟音樂世界。"})
    else:
        return jsonify({"success": False, "msg": f"🪙 時空金庫餘額不足！妳目前只有 {current_user.coins} 元，快去寫日誌或簽到賺錢吧！"})

@app.route('/api/game_rhythm_friends', methods=['GET'])
@login_required
def get_rhythm_game_friends():
    try:
        # 👥 1. 撈取目前使用者的所有已確認好友
        friendships = Friendship.query.filter(
            ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)) & 
            (Friendship.status == 'accepted')
        ).all()
        
        friend_list = []
        for f in friendships:
            # 判斷哪一邊才是好友的資料
            friend_user = f.receiver if f.user_id == current_user.id else f.sender
            
            if not friend_user:
                continue
                
            # 🎯 排除自己
            if friend_user.id == current_user.id:
                continue
            
            # 🎯 核心修正：強迫從資料庫重新整理，打破新舊帳號的快取隔閡
            try:
                db.session.refresh(friend_user)
            except Exception:
                pass 
            
            score_field_name = 'highest_score'
            if hasattr(friend_user, score_field_name):
                raw_score = getattr(friend_user, score_field_name, 0)
                
                # 💡 關鍵新戶防呆：如果新註冊的人欄位是 None，強迫在畫面上顯示 0 分，而不是直接崩潰或漏球
                h_score = int(raw_score) if (raw_score is not None and str(raw_score).isdigit()) else 0
            else:
                h_score = 0  
                
            # 📝 打包成前端需要的欄位名稱
            friend_list.append({
                "id": friend_user.id,
                "name": friend_user.nickname or friend_user.username or "新註冊時空旅人", 
                "high_score": h_score 
            })
            
        # 🛡️ 如果是新註冊帳號，通常在資料庫「沒有歷史好友」，這裡就是最關鍵的地方！
        # 為了不讓新註冊的玩家一進音遊畫面空空如也產生恐懼，我們給他動態保底對手！
        if not friend_list:
            friend_list = [
                {"id": 9991, "name": "官方小精靈殘影", "high_score": 85},
                {"id": 9992, "name": f"時空幻影-{current_user.nickname or current_user.username}", "high_score": 120}
            ]
            
        return jsonify({'success': True, 'friends': friend_list})
        
    except Exception as e:
        print("音遊好友 API 噴錯，原因:", e)
        return jsonify({
            'success': True, 
            'friends': [{"id": 9999, "name": "系統安全保底殘影", "high_score": 100}]
        })

@app.route('/api/upload_score', methods=['POST'])
@login_required
def game_upload_user_score_final():
    try:
        data = request.get_json() or {}
        new_score = int(data.get('score', 0)) 
        
        score_field_name = 'highest_score'
        is_new_record = False
        
        if hasattr(current_user, score_field_name):
            old_best = getattr(current_user, score_field_name, 0) or 0
            
            if new_score > old_best or old_best == 0:
                setattr(current_user, score_field_name, new_score)
                db.session.commit() # 🎯 確保存入資料庫
                
                # 🎯 核心補強：存入後立刻讓全域 session 釋放快取，確保別人的網頁下一次 fetch 能看到新分數
                db.session.expire_all() 
                
                is_new_record = True
                my_best = new_score
            else:
                my_best = old_best
        else:
            my_best = new_score
            is_new_record = True
            
        return jsonify({
            "success": True, 
            "is_new_record": is_new_record, 
            "my_best": my_best
        })
        
    except Exception as e:
        print("上傳分數失敗，原因:", e)
        db.session.rollback() 
        return jsonify({"success": False, "msg": "寫入分數失敗"})

# =================================================================
# 🎵 終極大絕招：音遊專屬且永不衝突的好友分數大廳 API
# =================================================================
@app.route('/api/rhythm_final_scores', methods=['GET'])
@login_required
def super_rhythm_friend_scores():
    try:
        # 👥 1. 精準撈取已確認的好友關係
        friendships = Friendship.query.filter(
            ((Friendship.user_id == current_user.id) | (Friendship.friend_id == current_user.id)) & 
            (Friendship.status == 'accepted')
        ).all()
        
        friend_list = []
        for f in friendships:
            # 🎯 【核心修正】精準判斷：只要不等於目前登入的 current_user.id，那個人才是真正的「好友」！
            if f.user_id != current_user.id:
                friend_user = f.sender
            else:
                friend_user = f.receiver
                
            # 🛡️ 安全防護：萬一因為某些髒資料導致撈出來的對象還是自己，直接跳過不加入列表！
            if friend_user.id == current_user.id:
                continue
            
            # 🎯 2. 讀取好友在 User 表裡的最高分
            h_score = getattr(friend_user, 'highest_score', 0) or 0
            
            friend_list.append({
                "id": friend_user.id,
                "name": friend_user.nickname,       # 傳送真正的對手暱稱
                "high_score": int(h_score)          # 傳送真正的對手最高分
            })
            
        return jsonify({'success': True, 'friends': friend_list})
        
    except Exception as e:
        print("終極音遊 API 篩選錯誤:", e)
        return jsonify({'success': False, 'msg': '無法讀取好友'})

@app.route('/buy_media', methods=['POST'])
@login_required
def buy_media():
    # 🌟 超級相容讀取法：管他前端用 JSON 還是 Form 表單送，通通都抓得到！
    if request.is_json:
        data = request.get_json() or {}
        price_val = data.get('price', 0)
        item_name = data.get('item_name', '')
        video_url = data.get('video_url', '').strip()
    else:
        price_val = request.form.get('price', 0)
        item_name = request.form.get('item_name', '')
        video_url = request.form.get('video_url', '').strip()

    price = int(price_val) if price_val else 0

    # 1. 檢查目前登入使用者的金幣是否足夠
    if current_user.coins < price:
        return jsonify({
            'success': False, 
            'message': f'您的心靈金幣不足！還差 {price - current_user.coins} 個。'
        })
    
    # 2. 扣除當前使用者的金幣
    current_user.coins -= price
    
    # 3. 🎯【精準寫入】只寫入目前登入的購買人格子
    current_user.current_video = video_url
    
    # 4. 儲存變更
    db.session.add(current_user)
    db.session.commit() 
    
    return jsonify({
        'success': True, 
        'new_balance': current_user.coins,
        'message': f'【{item_name}】購買成功！已為您更換專屬背景影片。'
    })
if __name__ == '__main__':
    with app.app_context():
        # 1. 確保基礎資料表都建立
        db.create_all()
        
        # 2. 🎯 自動補欄位魔法：檢查 user 表有沒有 current_video，沒有就手動補進去
        try:
            from sqlalchemy import text
            # 檢查 user 表
            db.session.execute(text("ALTER TABLE user ADD COLUMN current_video VARCHAR(255) DEFAULT NULL;"))
            db.session.commit()
            print("💡 已成功為 user 資料表自動補上 current_video 欄位！")
        except Exception:
            # 如果欄位早就存在了，它會噴錯，我們直接不管它（代表沒事）
            db.session.rollback()

        try:
            from sqlalchemy import text
            # 保險起見，連妳畫面上看到的 daily_records 表也檢查一下
            db.session.execute(text("ALTER TABLE daily_records ADD COLUMN current_video VARCHAR(255) DEFAULT NULL;"))
            db.session.commit()
            print("💡 已成功為 daily_records 資料表自動補上 current_video 欄位！")
        except Exception:
            db.session.rollback()

    # 3. 正常啟動伺服器app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  