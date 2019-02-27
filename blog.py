from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps  


#Login Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:   
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için giriş yapınız.")
            return redirect(url_for("login"))
    return decorated_function

#User Register Form
class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators= [validators.length(min=4, max= 25)])
    username = StringField("Kullanıcı Adı", validators=[validators.length(min=4, max=25)])
    email= StringField("Email Adresi",validators=[validators.Email(message="Lütfen geçerli bir email adresi yazın.")])
    password = PasswordField("Parola",validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyin."),
        validators.EqualTo(fieldname = "confirm", message= "Parolanız uyuşmuyor.")
    ])
    confirm = PasswordField("Parola Doğrula")


#User Login Form
class LoginForm(Form):
    username=StringField("Kullanıcı Adı")
    password = PasswordField("Parola")    



#Article Add Form
class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.length(min=5,max=50)])
    content = TextAreaField("Makale İçeriği",validators=[validators.length(min=10)])



app = Flask(__name__)

app.secret_key = "benimsifrem"

app.config["MYSQL_HOST"]= "localhost"
app.config["MYSQL_USER"]="root"
app.config["MYSQL_PASSWORD"]=""
app.config["MYSQL_DB"]="blog"
app.config["MYSQL_CURSORCLASS"]="DictCursor"

mysql = MySQL(app)


@app.route("/")
def layout():
    return render_template("layout.html")

@app.route("/about")
def about():
    return render_template("about.html")    

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles"
    result = cursor.execute(sorgu)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")    
    

#Control Panel
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where author = %s"
    result = cursor.execute(sorgu,(session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")    
    
#Delete Article
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where author = %s and id = %s"
    result = cursor.execute(sorgu,(session["username"],id))
    if result > 0:
        sorgu2="Delete from articles where id = %s"
        cursor.execute(sorgu2,(id))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok.")
        return redirect(url_for("layout"))


#Register
@app.route("/register", methods = ["GET","POST"])
def register(): 
    form = RegisterForm(request.form) 
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        sorgu = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit()
        cursor.close()

        flash("Başarıyla kayıt oldunuz")

        return redirect(url_for("login"))
    else:
        return render_template("register.html",form = form)   

#Login
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data
        cursor=mysql.connection.cursor()
        sorgu = "Select * From users where username = %s"
        result = cursor.execute(sorgu,(username,))
        if result > 0 : 
            data= cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered, real_password):
                flash("Başarıyla giriş yaptınız")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("layout"))
            else:
                flash("Parolanızı yanlış girdiniz")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor.")
            return redirect(url_for("login"))
        cursor.close()        
    return render_template("login.html",form = form)

#Exit
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("layout"))


#Add Article
@app.route("/addarticle", methods = ["GET","POST"])
def addarticle():    
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        sorgu = "Insert into articles(title,author,content) Values(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale başarıyla eklendi")
        return redirect(url_for("dashboard"))
    return render_template("addarticle.html", form=form)



@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where id=%s"
    result = cursor.execute(sorgu,(id,))
    if result > 0 :
        article = cursor.fetchone()
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")    


#Update Article
@app.route("/edit/<string:id>", methods = ["GET", "POST"])
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * From articles where id = %s and author=%s "
        result = cursor.execute(sorgu,(id,session["username"]))
        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok.")
            return redirect(url_for("layout"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]   
            return render_template("edit.html", form = form)
    else:
        form = ArticleForm(request.form)
        
        newTitle = form.title.data
        newContent = form.content.data
        
        sorgu2 = "Update articles Set title =%s, content=%s where id=%s"
		
        cursor = mysql.connection.cursor()
        
        cursor.execute(sorgu2,(newTitle,newContent,id))
		
        mysql.connection.commit()
		
        flash("Makale başarıyla güncellendi.")
		
        return redirect(url_for("dashboard"))	
     

#Searcg Article
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("layout"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()

        sorgu = "Select * From articles where title like '%" + keyword +"%' "

        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı.")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html", articles = articles)    


if __name__ == "__main__":
    app.run(debug=True)    
 