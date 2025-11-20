from flask import Flask, render_template, request, redirect, url_for
import json
import os
import tempfile, shutil
from werkzeug.utils import secure_filename

app = Flask(__name__)

# -----------------------------
# 1) 멤버 데이터 읽기
# -----------------------------
DATA_FILE = os.path.join(app.root_path, "data", "members.json")

def load_members():
    """members.json에서 members 리스트 가져오기"""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["members"]   

def get_member_by_username(username):
    """github_username으로 특정 멤버 한 명 찾기"""
    members = load_members()
    for m in members:
        if m.get("github_username") == username:
            return m
    return None

def save_members(members):
    """members 리스트를 members.json에 안전하게 저장"""
    dirpath = os.path.dirname(DATA_FILE)
    os.makedirs(dirpath, exist_ok=True)
    payload = {"members": members}

    # 임시 파일에 먼저 쓰고 교체 (부분 손상 방지)
    fd, tmp = tempfile.mkstemp(dir=dirpath, suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        shutil.move(tmp, DATA_FILE)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "files")
ALLOWED_EXTS = {"pdf", "png", "jpg", "jpeg", "zip", "pptx"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
# 파일 업로드
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS

# -----------------------------
# 2) 라우트 설정
# -----------------------------

# 메인 페이지 (Team)
@app.route("/")
def index():
    members = load_members()
    return render_template("index.html", members=members)

# 멤버 목록 페이지 (Member)
@app.route("/result")
def result():
    members = load_members()
    return render_template("result.html", members=members)
# /member 로 들어와도 /result 로 보내기
@app.route("/member")
def member_redirect():
    return redirect(url_for("result"))


# 멤버 상세 페이지: /result/<username>
@app.route("/result/<username>")
def member_detail(username):
    member = get_member_by_username(username)
    if member is None:
        return "Member not found", 404
    return render_template("member_detail.html", member=member)

# 멤버 수정 페이지: /input?username=...
@app.route("/input")
def input_page():
    username = request.args.get("username")
    member = get_member_by_username(username) if username else None
    return render_template("input.html", member=member, is_new=(member is None))

# 멤버 정보 업데이트 페이지
@app.route("/member/update", methods=["POST"])
def update_member():
    username = (
        (request.form.get("github_username") or "").strip()       # 수정 폼(hidden)
        or (request.form.get("github_username_new") or "").strip() # 신규 폼(text)
    )

    if not username:
        return "github_username is required", 400

    members = load_members()
    # 대상 멤버 찾기
    target = None
    for m in members:
        if m.get("github_username") == username:
            target = m
            break
    if not target:
        target = {
            "name": "",
            "english_name": "",
            "intro": "",
            "role": [],
            "major": [],
            "image": "memozi_subin.png", #기본이미지  
            "phone": "",
            "email": "",
            "github_username": username,
            "github_profile": f"https://github.com/{username}",
            "portfolio_link": "",
            "portfolio_file": "",
            "portfolio": []
        }
        members.append(target)

    # 단일 필드 업데이트
    target["name"] = (request.form.get("name") or "").strip()
    target["english_name"] = (request.form.get("english_name") or "").strip()
    target["intro"] = (request.form.get("intro") or "").strip()
    target["phone"] = (request.form.get("phone") or "").strip()
    target["email"] = (request.form.get("email") or "").strip()
    target["portfolio_link"] = (request.form.get("portfolio_link") or "").strip()
    auto_profile_url = f"https://github.com/{username}"
    target["github_profile"] = auto_profile_url

    # ✅ 다중 입력 필드(role[], major[]) 처리
    roles = [r.strip() for r in request.form.getlist("role[]") if r.strip()]
    majors = [m.strip() for m in request.form.getlist("major[]") if m.strip()]
    # 만약 input 이름이 role / major 단일로 왔다면 fallback
    if not roles and request.form.get("role"):
        roles = [x.strip() for x in request.form.get("role", "").split(",") if x.strip()]
    if not majors and request.form.get("major"):
        majors = [x.strip() for x in request.form.get("major", "").split(",") if x.strip()]

    target["role"] = roles if roles else target.get("role", [])
    target["major"] = majors if majors else target.get("major", [])

    # ✅ 파일 업로드 처리
    old_file = (request.form.get("portfolio_file_old") or "").strip()
    remove_flag = request.form.get("remove_portfolio_file") == "1"
    file = request.files.get("portfolio_upload")

    UPLOAD_DIR = app.config["UPLOAD_FOLDER"]
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    def safe_remove(path):
        """파일 안전 삭제"""
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    # -----------------------------
    # 1) 체크박스 눌렀을 때 → 파일 삭제
    # -----------------------------
    if remove_flag:
        if old_file:
            safe_remove(os.path.join(UPLOAD_DIR, old_file))
        target["portfolio_file"] = ""

    # -----------------------------
    # 2) 새 파일 업로드한 경우 → 교체
    # -----------------------------
    elif file and file.filename:
        if not allowed_file(file.filename):
            return "허용되지 않는 파일 형식입니다.", 400

        base = secure_filename(file.filename)
        save_name = base
        i = 1
        while os.path.exists(os.path.join(UPLOAD_DIR, save_name)):
            name, ext = os.path.splitext(base)
            save_name = f"{name}_{i}{ext}"
            i += 1

        # 파일 저장
        file.save(os.path.join(UPLOAD_DIR, save_name))

        # 이전 파일이 있으면 삭제
        if old_file and old_file != save_name:
            safe_remove(os.path.join(UPLOAD_DIR, old_file))

        # 새 파일명 반영
        target["portfolio_file"] = save_name

    # -----------------------------
    # 3) 아무것도 안 한 경우 → 기존 유지
    # -----------------------------
    else:
        # 파일 관련 변경이 없으면 기존 파일 그대로 둠
        target["portfolio_file"] = old_file


    # ✅ 포트폴리오 항목들 (다중)
    titles = request.form.getlist("project_title[]")
    periods = request.form.getlist("period[]")      
    proles  = request.form.getlist("proj_role[]")
    descs   = request.form.getlist("description[]")

    portfolio = []
    for i in range(max(len(titles), len(periods), len(proles), len(descs))):
      t = (titles[i] if i < len(titles) else "").strip()
      prd = (periods[i] if i < len(periods) else "").strip()
      rl = (proles[i] if i < len(proles) else "").strip()
      ds = (descs[i] if i < len(descs) else "").strip()
      if any([t, prd, rl, ds]):   
          portfolio.append({
              "project_title": t,
              "period": prd,
              "role": rl,
              "description": ds
          })

    target["portfolio"] = portfolio

    # 저장
    save_members(members)

    # 완료 후 상세 페이지로
    return redirect(url_for("member_detail", username=username))



# 비상 연락망 페이지
@app.route("/contact")
def contact():
    members = load_members()
    return render_template("contact.html", members=members)

def delete_file_safely(path):
    """존재하면 조용히 삭제"""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def is_file_used_by_others(members, key, filename, except_username=None):
    """같은 파일명을 다른 멤버가 쓰는지 확인 (중복 사용 방지용)"""
    if not filename:
        return True  
    for m in members:
        if m.get("github_username") == except_username:
            continue
        if m.get(key) == filename:
            return True
    return False

@app.route("/member/delete", methods=["POST"])
def delete_member():
    username = (request.form.get("github_username") or "").strip()
    if not username:
        return "github_username is required", 400

    members = load_members()

    # 대상 멤버 찾기
    idx = None
    target = None
    for i, m in enumerate(members):
        if m.get("github_username") == username:
            idx = i
            target = m
            break

    if idx is None:
        return "Member not found", 404

    # 삭제 전에 첨부 파일 정리
    static_root = app.static_folder

    # 1) 포트폴리오 파일
    pf_file = target.get("portfolio_file")
    if pf_file and not is_file_used_by_others(members, "portfolio_file", pf_file, except_username=username):
        delete_file_safely(os.path.join(static_root, "files", pf_file))

    # 2) 프로필 이미지 (기본 이미지면 건드리지 않음)
    img_file = target.get("image")
    default_images = {"default.png", "default.jpg", "default.jpeg", "default.webp"}
    if img_file and img_file not in default_images:
        if not is_file_used_by_others(members, "image", img_file, except_username=username):
            delete_file_safely(os.path.join(static_root, "img", img_file))

    # 실제 멤버 제거
    del members[idx]
    save_members(members)

    # 목록으로
    return redirect(url_for("result"))

# -----------------------------
# 3) 앱 실행
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)