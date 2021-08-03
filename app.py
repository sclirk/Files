from flask import Flask, flash, render_template, request, redirect, url_for, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql.expression import func

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1111@localhost:5432/Users'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "random_secret_key"
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


class BaseData(db.Model):
    __tablename__ = 'base_data'
    id = db.Column(db.INTEGER(), nullable=False, primary_key=True)
    login = db.Column(db.VARCHAR(50), nullable=False)
    password = db.Column(db.VARCHAR(50), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        print(password)
        return check_password_hash(generate_password_hash(password), password)

    def __repr__(self):
        return "<{}>".format(self.login)

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id


class FilesDataBase(db.Model):
    __tablename__ = "files"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String())
    content = db.Column(db.String())
    folder = db.Column(db.String())

    def __init__(self, id, filename, content, folder):
        self.id = id
        self.filename = filename
        self.content = content
        self.folder = folder

    def __repr__(self):
        return f"{self.filename}"


class FolderDataBase(db.Model):
    __tablename__ = "folders"

    id = db.Column(db.Integer, primary_key=True)
    folder_name = db.Column(db.String())

    def __init__(self, id, folder_name):
        self.id = id
        self.folder_name = folder_name

    def __repr__(self):
        return f"{self.folder_name}"


class User(db.Model, UserMixin):
    __tablename__ = 'base_data'


@login_manager.user_loader
def load_user(user_login):
    return db.session.query(User).get(user_login)


@app.route('/login/', methods=['post', 'get'])
def login():
    if request.method == "POST":
        login = request.form['login']
        password = request.form['password']
        user = db.session.query(BaseData).filter(BaseData.login == login).first()

        if current_user.is_authenticated is True:
            flash("You are already logged in", 'error')
        else:

            if user and check_password_hash(user.password, password) is True:
                login_user(user)
                return redirect(url_for('admin'))
            flash("Invalid username/password", 'error')

    return render_template('login.html')


@login_required
@app.route('/update_file/<string:folder>', methods=['GET', 'POST'])
def update_file(folder):

    content = (dict(zip(db.session.query(FilesDataBase.filename).filter(FilesDataBase.id is not None
                                                                        and FilesDataBase.folder == folder).all(),
                        db.session.query(FilesDataBase.content).filter(FilesDataBase.id is not None
                                                                       and FilesDataBase.folder == folder).all())))

    return render_template("files_browser.html", content=content)


@login_required
@app.route('/update_folder/<string:value>', methods=['GET', 'POST'])
def update_folder(value):
    employee = FolderDataBase.query.filter_by(folder_name=value).first()
    id = db.session.query(FolderDataBase.id).filter(FolderDataBase.folder_name == value).first()
    if request.method == 'POST':
        db.session.delete(employee)
        db.session.commit()
        folder_name = request.form['folder_name']
        FilesDataBase.query.filter_by(folder=value).update({'folder': folder_name})
        employee = FolderDataBase(id=id[0], folder_name=folder_name)
        db.session.add(employee)
        db.session.commit()

        return redirect('/')

    return render_template("update_page.html", employee=employee)


@login_required
@app.route('/update_content/<string:filename>', methods=['GET', 'POST'])
def update_content(filename):
    folder_list = FolderDataBase.query.all()
    employee = FilesDataBase.query.filter_by(filename=filename).first()
    id = db.session.query(FilesDataBase.id).filter(FilesDataBase.filename == filename).first()
    if request.method == 'POST':
        db.session.delete(employee)
        db.session.commit()
        filename_upd = request.form['filename']
        content_upd = request.form['content']
        folder_upd = request.form['folder']
        db_queue = FilesDataBase(id=id[0], filename=filename_upd, content=content_upd, folder=folder_upd)
        db.session.add(db_queue)
        db.session.commit()

        return redirect('/')

    return render_template("update_files_page.html", employee=employee, folders=folder_list)


@app.route('/registration', methods=['POST', "GET"])
def registration():
    if request.method == "POST":
        login_form = request.form['login']
        password = request.form['password']
        id_login = db.session.query(func.max(BaseData.id)).one()
        repeating_login = True if db.session.query(BaseData).filter(BaseData.login == login_form).first() else False
        creator = BaseData(id=id_login[0] + 1, login=login_form, password=generate_password_hash(password))
        if repeating_login is False:
            db.session.add(creator)
            db.session.commit()
            return redirect('/')
        else:
            flash("This login is already taken/Entering value is not correct", 'error')
            return render_template('registration.html')
    else:
        return render_template('registration.html')


@app.route('/create_folder/', methods=['GET', 'POST'])
def create_folder():
    if request.method == 'GET':
        return render_template('create_folder.html')

    if request.method == 'POST':
        id_folder = db.session.query(func.max(FolderDataBase.id)).one()
        folder_id_logic = 1 if id_folder[0] is None else id_folder[0] + 1
        folder_name = request.form['folder_name']
        queue_folder_create = FolderDataBase(id=folder_id_logic, folder_name=folder_name)
        db.session.add(queue_folder_create)
        db.session.commit()
        return redirect('/')


@app.route('/create_file/', methods=['GET', 'POST'])
def create_file():
    if request.method == 'GET':
        folder_list = FolderDataBase.query.all()

        return render_template('create_file.html', folders=folder_list)

    if request.method == 'POST':
        try:
            id_file = db.session.query(func.max(FilesDataBase.id)).one()
            id_logic_file = 1 if id_file[0] is None else id_file[0] + 1
            filename = request.form['filename']
            content = request.form['content']
            folder_name = request.form['folder']

            queue_folder_create = FilesDataBase(id=id_logic_file, filename=filename, content=content, folder=folder_name)
            db.session.add(queue_folder_create)
            db.session.commit()
            return redirect('/')
        except Exception:

            return redirect('/')


@app.route('/delete_folder/<string:folder>', methods=['GET'])
def delete_folder(folder):
    queue_delete_folder = FolderDataBase.query.filter_by(folder_name=folder).first()
    if request.method == 'GET':
        delete_files_folder = FilesDataBase.query.filter_by(folder=folder).first()
        db.session.delete(queue_delete_folder)
        db.session.commit()
        try:
            db.session.delete(delete_files_folder)
            db.session.commit()
        except Exception:
            return redirect('/')
        return redirect('/')

    return redirect('/')


@app.route('/delete_file/<string:file>', methods=['GET'])
def delete_file(file):
    queue_delete_file = FilesDataBase.query.filter_by(filename=file).first()
    if request.method == 'GET':
        db.session.delete(queue_delete_file)
        db.session.commit()

        return redirect('/')

    return redirect('/')


@app.route('/admin/')
@login_required
def admin():
    return render_template('admin.html')


@app.route('/')
def home():
    content = (dict(zip(db.session.query(FolderDataBase).filter(FolderDataBase.id is not None).all(),
                        db.session.query(FolderDataBase.id).filter(FolderDataBase.id is not None).all())))
    return render_template('page.html', content=content)


@app.route('/logout/')
@login_required
def logout():
    logout_user()
    return render_template('logout.html')


if __name__ == '__main__':
    db.create_all()
    app.run(debug=False)
