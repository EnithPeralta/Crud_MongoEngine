import base64
from io import BytesIO
import os
import threading
from tkinter import Image
from bson import ObjectId
from flask import Flask, jsonify, redirect, request,render_template,session, url_for,flash
from mongoengine import connect,DoesNotExist
import pymongo
import yagmail
from bson.errors import InvalidId

app = Flask(__name__)
app.config['MONGODB_SETTINGS'] = {
    'db': 'Drogeria',
    'host': 'localhost',
    'port': 27017
}
connect(**app.config['MONGODB_SETTINGS'])

from models.models import Usuarios,Productos,Categorias

@app.route('/')
def inicio():
    return render_template('home.html')

@app.route('/users', methods=['GET'])
def get_users():
    users = Usuarios.objects()
    return jsonify([user.to_json() for user in users]), 200

@app.route('/users', methods=['POST'])
def add_user():
    data = request.json
    user = Usuarios(
        usuario=data['usuario'],
        password=data['password'],
        nombre=data['nombre'],
        apellido=data['apellido'],
        email=data['email']
    )
    user.save()
    return 'Usuario creado correctamente', 201

@app.route('/iniciarSesion', methods=['POST'])
def iniciarSesion():
    mensaje = None
    estado = False
    try:
        usuario = request.form['usuario']
        password = request.form['password']
        user = Usuarios.objects(usuario=usuario, password=password).first()
        if user:
            email = yagmail.SMTP("mosqueraperalta12@gmail.com", open(".password").read(), encoding='UTF-8')
            asunto = 'Reporte de ingreso al sistema de usuario'
            mensaje = f"Se informa que el usuario <b>'{user.nombre} {user.apellido}'</b> ha ingresado al sistema"
            thread = threading.Thread(target=enviarCorreo, args=(email, [user.email], asunto, mensaje ))
            thread. start()
            estado = True
            return redirect("/home")  
        else:
            mensaje = 'Credenciales no válidas'            
    except pymongo.errors.PyMongoError as error: 
        mensaje = error
    return render_template('home.html', estado=estado, mensaje=mensaje)

def enviarCorreo(email=None, destinatario=None, asunto=None, mensaje=None):
    email. send (to=destinatario, subject=asunto, contents=mensaje)

@app.route('/home')
def home():
    if 'user' in session:
        try:
            listaProductos = Productos.objects.all()
            listaP = []
            for p in listaProductos:
                try:
                    categoria = Categorias.objects.get(id=p.categoria.id)
                    p.nombreCategoria = categoria.nombre
                    listaP.append(p)
                except DoesNotExist:
                    # Manejar el caso donde la categoría no existe
                    p.nombreCategoria = 'Categoría no encontrada'
                    listaP.append(p)
            return render_template('listaProducto.html', Productos=listaP)
        except Exception as e:
            # Manejar otras excepciones generales
            return render_template('error.html', error=str(e))
    else:
        mensaje = "Debe primero ingresar con sus credenciales"
        return render_template("listaProducto.html", mensaje=mensaje)    
    
@app.route('/agregarProductoJson', methods=['GET', 'POST'])
#Recibimos los datos del formulario del name
def agregarProductoJson():
    if request.method == 'POST':
        codigo = request.form['codigo']
        nombre = request.form['nombre']
        precio = request.form['precio']
        categoria = ObjectId(request.form['cbCategoria'])
        foto = request.files['fileFoto']

        # Verificar si el código del producto ya existe en la base de datos
        if Productos.objects(codigo=codigo).first():
            flash('Ya existe un producto con ese código', 'error')
            return redirect(url_for('agregarProductoJson'))

        # Si el código no existe se guarda en la base de datos
        producto = Productos(
            codigo=codigo,
            nombre=nombre,
            precio=precio,
            categoria=categoria,
            foto=foto.filename
        )
        producto.save() #Esta es la instruccion que guarda el producto

        flash('Producto agregado correctamente', 'success') #Flask  es para mostrar los mensajes desde el lado del cliente
        return redirect(url_for('agregarProductoJson'))

    else:
        productos = Productos.objects().all()
        return render_template('agregar.html', productos=productos)
    
@app.route("/consultar/<codigo>", methods=["GET"])
def consultar(codigo):
    if "user" in session:
        producto = Productos.objects(codigo=codigo).first()
        listaCategorias = Categorias.objects()
        return render_template("editar.html", categorias=listaCategorias, producto=producto)
    
@app.route("/editarProductoJson", methods=["PUT"])
def editarProductoJson():
    estado = False
    mensaje = None
    if "user" in session:
        try:
            datos = request.json
            datosProducto = datos.get('producto')
            fotoBase64 = datos.get('foto')['foto']
            idProducto = ObjectId(datosProducto['id'])
            producto = Productos.objects(id=idProducto).first()
            if producto:
                producto.codigo = int(datosProducto['codigo'])
                producto.nombre = datosProducto['nombre']
                producto.precio = int(datosProducto['precio'])
                producto.categoria = ObjectId(datosProducto['categoria'])
                producto.save()
                if fotoBase64:
                    rutaImagen = f"{os.path.join(app.config['UPLOAD_FOLDER'], str(producto.id))}.jpg"
                    fotoBase64 = fotoBase64[fotoBase64.index(',') + 1:]
                    imagenDecondificada = base64.b64decode(fotoBase64)
                    imagen = Image.open(BytesIO(imagenDecondificada))
                    imagenJpg = imagen.convert("RGB")
                    imagenJpg.save(rutaImagen)
                mensaje = "Producto Actualizado Correctamente"
                estado = True
        except Exception as error:
            mensaje = str(error)
    else:
        mensaje = "Debe primero ingresar con sus credenciales"

    retorno = {"estado": estado, "mensaje": mensaje}
    return jsonify(retorno)

@app.route("/eliminarJson/<id>", methods=["DELETE"])
def eliminarJson(id):
    estado = False
    mensaje = None
    if "user" in session:
        try:
            producto = Productos.objects(id=id).first()
            if producto:
                producto.delete()
                mensaje = "Producto Eliminado Correctamente"
                estado = True
            else:
                mensaje = "No existe producto con ese Id"
        except Exception as error:
            mensaje = str(error)

    else:
        mensaje = "Debe primero ingresar con sus credenciales"

    retorno = {"estado": estado, "mensaje": mensaje}
    return jsonify(retorno)

app.secret_key = 'your_secret_key_here'  # Reemplazar con una clave única y secreta
@app.route('/salir')
def salir():
  session.clear() # Elimina todas las variables de la sesión
  mensaje = 'Ha cerrado la sesión' # Mensaje para mostrar al usuario
  return render_template('/home.html', mensaje=mensaje) # Redirige a la página de home con un mensaje

if __name__ == "__main__":
    app.run(debug=True)