import json
import random
import hashlib
import mysql.connector
import base64
import shutil
import ssl
from wsgiref.simple_server import make_server
from datetime import datetime
from pathlib import Path
from bottle import route, run, template, post, request, static_file, BaseRequest, default_app

BaseRequest.MEMFILE_MAX = 5 * 1024 * 1024

def validar_ruta_imagen(ruta_bd):
	directorio_img = Path("img").resolve()
	ruta_resuelta  = (Path(".") / ruta_bd).resolve()
 
	# str.startswith() compara la ruta absoluta resuelta contra el
	# directorio permitido. Si no empieza con él, está fuera.
	if not str(ruta_resuelta).startswith(str(directorio_img)):
		return None  # ruta inválida o maliciosa
 
	return ruta_resuelta



def loadDatabaseSettings(pathjs):
	pathjs = Path(pathjs)
	sjson = False
	if pathjs.exists():
		with pathjs.open() as data:
			sjson = json.load(data)
	return sjson
	
"""
function loadDatabaseSettings(pathjs):
	string = file_get_contents(pathjs);
	json_a = json_decode(string, true);
	return json_a;

"""
def getToken():
	tiempo = datetime.now().timestamp()
	numero = random.random()
	cadena = str(tiempo) + str(numero)
	numero2 = random.random()
	cadena2 = str(numero)+str(tiempo)+str(numero2)
	m = hashlib.sha1()
	m.update(cadena.encode())
	P = m.hexdigest()
	m = hashlib.md5()
	m.update(cadena.encode())
	Q = m.hexdigest()
	return f"{P[:20]}{Q[20:]}"

"""
*/ 
# Registro
/*
 * Este Registro recibe un JSON con el siguiente formato
 * 
 * : 
 *		"uname": "XXX",
 *		"email": "XXX",
 * 		"password": "XXX"
 * 
 * */
"""
@post('/Registro')
def Registro():
	dbcnf = loadDatabaseSettings('db.json');
	db = mysql.connector.connect(
		host='localhost', port = dbcnf['port'],
		database = dbcnf['dbname'],
		user = dbcnf['user'],
		password = dbcnf['password']
	)
	####/ obtener el cuerpo de la peticion
	if not request.json:
		return {"R":-1}
	R = 'uname' in request.json and 'email' in request.json and 'password' in request.json
	# TODO checar si estan vacio los elementos del json
	if not R:
		return {"R":-1}
	# TODO validar correo en json
	# TODO Control de error de la DB
	R = False
	uname    = request.json["uname"]
	email    = request.json["email"]
	password = request.json["password"]
	try:
		with db.cursor() as cursor:
			cursor.execute(
                'INSERT INTO Usuario VALUES (NULL, %s, %s, MD5(%s))',
                (uname, email, password)
            )
			R = cursor.lastrowid
			db.commit()
		db.close()
	except Exception as e:
		print(e) 
		return {"R":-2}
	return {"R":0,"D":R}




"""
/*
 * Este Registro recibe un JSON con el siguiente formato
 * 
 * : 
 *		"uname": "XXX",
 * 		"password": "XXX"
 * 
 * 
 * Debe retornar un Token 
 * */
"""

@post('/Login')
def Login():
	dbcnf = loadDatabaseSettings('db.json');
	db = mysql.connector.connect(
		host='localhost', port = dbcnf['port'],
		database = dbcnf['dbname'],
		user = dbcnf['user'],
		password = dbcnf['password']
	)
	###/ obtener el cuerpo de la peticion
	if not request.json:
		return {"R":-1}
	######/
	R = 'uname' in request.json  and 'password' in request.json
	# TODO checar si estan vacio los elementos del json
	if not R:
		return {"R":-1}
	
	# TODO validar correo en json
	# TODO Control de error de la DB
	uname    = request.json["uname"]
	password = request.json["password"]
	R = False
	try:
		with db.cursor() as cursor:
			cursor.execute(
                'SELECT id FROM Usuario WHERE uname = %s AND password = MD5(%s)',
                (uname, password)
            )			
			R = cursor.fetchall()
	except Exception as e: 
		print(e)
		db.close()
		return {"R":-2}
	
	
	if not R:
		db.close()
		return {"R":-3}
	
	T = getToken();
	#file_put_contents('/tmp/log','insert into AccesoToken values('.R[0].',"'.T.'",now())');
	with open("/tmp/log","a") as log:
		log.write(f'Delete from AccesoToken where id_Usuario = "{R[0][0]}"\n')
		log.write(f'insert into AccesoToken values({R[0][0]},"{T}",now())\n')
	
	
	try:
		with db.cursor() as cursor:
			cursor.execute(
                'DELETE FROM AccesoToken WHERE id_Usuario = %s',
                (R[0][0],)
            )
			cursor.execute(
                'INSERT INTO AccesoToken VALUES (%s, %s, NOW())',
                (R[0][0], T)
            )
			db.commit()
			db.close()
			return {"R":0,"D":T}
	except Exception as e:
		print(e)
		db.close()
		return {"R":-4}

"""
/*
 * Este subir imagen recibe un JSON con el siguiente formato
 * 
 * 
 * 		"token: "XXX"
 *		"name": "XXX",
 * 		"data": "XXX",
 * 		"ext": "PNG"
 * 
 * 
 * Debe retornar codigo de estado
 * */
"""
@post('/Imagen')
def Imagen():
	#Directorio
	tmp = Path('tmp')
	if not tmp.exists():
		tmp.mkdir()
	img = Path('img')
	if not img.exists():
		img.mkdir()
	
	###/ obtener el cuerpo de la peticion
	if not request.json:
		return {"R":-1}
	######/
	R = 'name' in request.json  and 'data' in request.json and 'ext' in request.json  and 'token' in request.json
	# TODO checar si estan vacio los elementos del json
	if not R:
		return {"R":-1}
	
	dbcnf = loadDatabaseSettings('db.json');
	db = mysql.connector.connect(
		host='localhost', port = dbcnf['port'],
		database = dbcnf['dbname'],
		user = dbcnf['user'],
		password = dbcnf['password']
	)

	# Validar si el usuario esta en la base de datos
	TKN = request.json['token'];
	
	R = False
	try:
		with db.cursor() as cursor:
			cursor.execute(
                'SELECT id_Usuario FROM AccesoToken WHERE token = %s',
                (TKN,)
            )			
			R = cursor.fetchall()
	except Exception as e: 
		print(e)
		db.close()
		return {"R":-2}
	
	
	id_Usuario = R[0][0];
	name = request.json['name']
	ext  = request.json['ext']
	with open(f'tmp/{id_Usuario}',"wb") as imagen:
		imagen.write(base64.b64decode(request.json['data'].encode()))
	
	############################
	############################
	# Guardar info del archivo en la base de datos
	try:
		with db.cursor() as cursor:
			cursor.execute(
                'INSERT INTO Imagen VALUES (NULL, %s, %s, %s)',
                (name, 'img/', id_Usuario)
            )
            # FIX SQL INJECTION: id_Usuario parametrizado en el SELECT
			cursor.execute(
                'SELECT MAX(id) AS idImagen FROM Imagen WHERE id_Usuario = %s',
                (id_Usuario,)
            )

			R = cursor.fetchall()
			idImagen = R[0][0]
			nueva_ruta = f'img/{idImagen}.{ext}'
 
            # FIX SQL INJECTION: ruta e id parametrizados en el UPDATE
			cursor.execute(
                'UPDATE Imagen SET ruta = %s WHERE id = %s',
                (nueva_ruta, idImagen)
            )

			db.commit()
			# Mover archivo a su nueva locacion
			shutil.move('tmp/'+str(id_Usuario),'img/'+str(idImagen)+'.'+str(request.json['ext']))
			return {"R":0,"D":idImagen}
	except Exception as e: 
		print(e)
		db.close()
		return {"R":-3}
	
"""
/*
 * Este Registro recibe un JSON con el siguiente formato
 * 
 * : 
 * 		"token: "XXX",
 * 		"id": "XXX"
 * 
 * 
 * Debe retornar un Token 
 * */
"""

@post('/Descargar')
def Descargar():
	dbcnf = loadDatabaseSettings('db.json');
	db = mysql.connector.connect(
		host='localhost', port = dbcnf['port'],
		database = dbcnf['dbname'],
		user = dbcnf['user'],
		password = dbcnf['password']
	)
	
	
	###/ obtener el cuerpo de la peticion
	if not request.json:
		return {"R":-1}
	######/
	R = 'token' in request.json and 'id' in request.json  
	# TODO checar si estan vacio los elementos del json
	if not R:
		return {"R":-1}
	
	# TODO validar correo en json
	# Comprobar que el usuario sea valido
	TKN = request.json['token'];
	idImagen = request.json['id'];
	
	R = False
	try:
		with db.cursor() as cursor:
			cursor.execute(
                'SELECT id_Usuario FROM AccesoToken WHERE token = %s',
                (TKN,)
            )			
			R = cursor.fetchall()
	except Exception as e: 
		print(e)
		db.close()
		return {"R":-2}
		
	
	
	# Buscar imagen y enviarla
	
	try:
		with db.cursor() as cursor:
			cursor.execute(
                'SELECT name, ruta FROM Imagen WHERE id = %s AND id_Usuario = %s',
                (idImagen, id_Usuario)
            )			
			R = cursor.fetchall()
	except Exception as e: 
		print(e)
		db.close()
		return {"R":-3}
	
	if not R:
		db.close()
		return {"R": -5}  # Imagen no encontrada o no pertenece al usuario
 
	ruta_bd = R[0][1]

	ruta_valida = validar_ruta_imagen(ruta_bd)
 
	if ruta_valida is None:
		db.close()
		return {"R": -6}  # Ruta fuera del directorio permitido — ataque bloqueado
 
	# Servir usando nombre de archivo + directorio img/ por separado
	# para que Bottle no pueda navegar fuera de ese directorio
	directorio_img = Path("img").resolve()
	nombre_archivo = ruta_valida.name
 
	return static_file(nombre_archivo, root=str(directorio_img))

	
if __name__ == '__main__':
    # Creamos el contexto de seguridad SSL
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain('cert.pem', 'key.pem')

    # Levantamos el servidor nativo de Python y le inyectamos la seguridad
    app = default_app()
    server = make_server('localhost', 8080, app)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)


    print(" Servidor HTTPS seguro corriendo en https://localhost:8080/")
    server.serve_forever()
