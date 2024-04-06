import base64
from io import BytesIO
import os
import threading
from tkinter import Image
from bson import ObjectId
from flask import Flask, jsonify, redirect, request,render_template,session
from mongoengine import connect
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
    listaProductos = Productos.objects.all()
    listaP = []
    for p in listaProductos:
        categoria = Categorias.objects.get(id=p.categoria.id)
        p.nombreCategoria = categoria.nombre
        listaP.append(p)
    return render_template('listaProducto.html', Productos=listaP)

@app.route('/listaProductos')
def listaProductos():
    if "user" in session:
        listaProductos = Productos.objects()
        return render_template("listaProducto.html", productos=listaProductos)
    else:
        mensaje = "Debe primero ingresar con sus credenciales"
        return render_template("home.html", mensaje=mensaje)


@app.route('/vistaAgregarProducto')
def vistaAgregarProducto():
    if "user" in session:
        listaCategorias = Categorias.objects()
        return render_template("agregar.html", categorias=listaCategorias)
    else:
        mensaje = "Debe primero ingresar con sus credenciales"
        return render_template("home.html", mensaje=mensaje)


@app.route("/agregarProductoJson", methods=['GET','POST'])
def agregarProductoJson():
    mensaje = ""
    estado = False
    if "user" in session:
        try:
            datos = request.json
            print(datos)
            datosProducto = datos.get('producto')
            print(datosProducto)
            fotoBase64 = datos.get('foto')["foto"]

            producto = Productos(**datosProducto)
            print(producto.precio)

            producto.save()

            if producto.id:
                rutaImagen = f"{os.path.join(app.config['UPLOAD_FOLDER'], str(producto.id))}.jpg"
                fotoBase64 = fotoBase64[fotoBase64.index(',') + 1:]

                fotoDecodificada = base64.b64decode(fotoBase64)

                with open(rutaImagen, "wb") as f:
                    f.write(fotoDecodificada)

                mensaje = "Producto agregado correctamente"
                estado = True
            else:
                mensaje = "Error al agregar el producto"
                estado = False
        except Exception as e:
            print(e)
            mensaje = "Error al agregar el producto"
            estado = False
    else:
        mensaje = "Debe primero ingresar con sus credenciales"

    return jsonify({"mensaje": mensaje, "estado": estado})

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