from flask import Flask, render_template, json, send_from_directory, abort, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_la_entrega_unab' 

# Carpetas físicas
FOLDER_MATERIAL = os.path.join(app.root_path, 'static', 'material')
app.config['UPLOAD_FOLDER'] = FOLDER_MATERIAL

ADMIN_USER = "admin"
ADMIN_PASS = "unab2026"

# Diccionario global para vincular IDs con nombres limpios
DICCIONARIO_CARRERAS = {
    "programacion": "Tecnicatura en Programación", "ciencia_datos_tec": "Tecnicatura en Ciencia de Datos",
    "gestion_org": "Tecnicatura en Gestión de las Organizaciones", "acompanamiento_ter": "Tecnicatura en Acompañamiento Terapéutico",
    "automatizacion": "Tecnicatura en Automatización y Control", "comunicacion_dig": "Tecnicatura en Comunicación Digital",
    "diseno_producto": "Tecnicatura en Diseño y Desarrollo de Producto", "logistica_tec": "Tecnicatura en Logística y Transporte",
    "protesis_dental": "Tecnicatura en Prótesis Dental", "administracion": "Licenciatura en Administración",
    "enfermeria": "Licenciatura en Enfermería", "ciencia_datos_lic": "Licenciatura en Ciencia de Datos",
    "ciencia_politica": "Licenciatura en Ciencia Política", "logistica_lic": "Licenciatura en Logística y Transporte",
    "ensenanza_mat": "Licenciatura en Enseñanza de la Matemática"
}

class Materia:
    def __init__(self, datos_materia):
        self.id = int(datos_materia.get("id"))
        self.nombre = datos_materia.get("nombre")
        self.anio = datos_materia.get("anio")
        self.cuatrimestre = datos_materia.get("cuatrimestre")
        self.horas = datos_materia.get("horas")
        self.correlativas = datos_materia.get("correlativas", [])
        self.archivo_pdf = datos_materia.get("archivo_pdf")
        self.materiales = datos_materia.get("materiales", [])

class GestorCarrera:
    def __init__(self, archivo_json):
        self.archivo_json = archivo_json

    def obtener_materias_por_carrera(self, carrera_id):
        with open(self.archivo_json, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        lista_diccionarios = datos.get(carrera_id, [])
        return [Materia(m) for m in lista_diccionarios]

    def actualizar_materia(self, carrera_id, materia_id, nuevos_datos, pdf_programa, pdf_material_nuevo):
        with open(self.archivo_json, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        
        for m in datos.get(carrera_id, []):
            if int(m['id']) == int(materia_id):
                m['nombre'] = nuevos_datos['nombre']
                m['horas'] = str(nuevos_datos['horas'])
                m['anio'] = nuevos_datos['anio']
                m['cuatrimestre'] = nuevos_datos['cuatrimestre']
                
                if pdf_programa:
                    m['archivo_pdf'] = pdf_programa
                
                if 'materiales' not in m or m['materiales'] is None:
                    m['materiales'] = []
                if pdf_material_nuevo:
                    if pdf_material_nuevo not in m['materiales']:
                        m['materiales'].append(pdf_material_nuevo)
                break
                
        with open(self.archivo_json, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)

    def eliminar_material_extra(self, carrera_id, materia_id, nombre_archivo):
        with open(self.archivo_json, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            
        for m in datos.get(carrera_id, []):
            if int(m['id']) == int(materia_id):
                if 'materiales' in m and nombre_archivo in m['materiales']:
                    m['materiales'].remove(nombre_archivo)
                break
                
        with open(self.archivo_json, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)

gestor = GestorCarrera('materias.json')

@app.route('/')
def home():
    # Renderizado estético de la portada
    tecnicaturas = [{"id": k, "nombre": v} for k, v in DICCIONARIO_CARRERAS.items() if "Tecnicatura" in v]
    licenciaturas = [{"id": k, "nombre": v} for k, v in DICCIONARIO_CARRERAS.items() if "Licenciatura" in v]
    return render_template('carreras.html', tecnicaturas=tecnicaturas, licenciaturas=licenciaturas)

@app.route('/carrera/<carrera_id>')
def ver_carrera(carrera_id):
    if carrera_id not in DICCIONARIO_CARRERAS: abort(404)
    lista_objetos_materias = gestor.obtener_materias_por_carrera(carrera_id)
    return render_template('index.html', materias=lista_objetos_materias, nombre_carrera=DICCIONARIO_CARRERAS[carrera_id], carrera_id=carrera_id)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USER and request.form['password'] == ADMIN_PASS:
            session['admin_logueado'] = True
            return redirect(url_for('panel_admin'))
        flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logueado', None)
    return redirect(url_for('home'))

# --- PANEL ADMIN SELECCIONABLE ---
@app.route('/admin')
def panel_admin():
    if not session.get('admin_logueado'): return redirect(url_for('login'))
    
    # Capturamos qué carrera quiere ver el admin (por defecto 'programacion')
    carrera_seleccionada = request.args.get('carrera', 'programacion')
    
    materias = gestor.obtener_materias_por_carrera(carrera_seleccionada)
    return render_template('admin.html', materias=materias, carreras=DICCIONARIO_CARRERAS, seleccionada=carrera_seleccionada)

@app.route('/admin/editar/<carrera_id>/<int:materia_id>', methods=['POST'])
def editar_materia(carrera_id, materia_id):
    if not session.get('admin_logueado'): return redirect(url_for('login'))
        
    datos_editados = {
        "nombre": request.form['nombre'], "horas": request.form['horas'],
        "anio": request.form['anio'], "cuatrimestre": request.form['cuatrimestre']
    }
    prog_final, mat_final = None, None
    if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])

    if 'archivo_programa' in request.files:
        f = request.files['archivo_programa']
        if f.filename != '':
            prog_final = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], prog_final))
            
    if 'archivo_material_nuevo' in request.files:
        f = request.files['archivo_material_nuevo']
        if f.filename != '':
            mat_final = secure_filename(f.filename)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], mat_final))
    
    gestor.actualizar_materia(carrera_id, materia_id, datos_editados, prog_final, mat_final)
    flash('¡Materia actualizada correctamente!', 'success')
    return redirect(url_for('panel_admin', carrera=carrera_id))

@app.route('/admin/eliminar-material/<carrera_id>/<int:materia_id>/<nombre_archivo>')
def borrar_archivo(carrera_id, materia_id, nombre_archivo):
    if not session.get('admin_logueado'): return redirect(url_for('login'))
    gestor.eliminar_material_extra(carrera_id, materia_id, nombre_archivo)
    flash(f'Se eliminó "{nombre_archivo}".', 'warning')
    return redirect(url_for('panel_admin', carrera=carrera_id))

# --- RUTAS DE DESCARGA REAL DE ARCHIVOS ---
@app.route('/descargar-material/<filename>')
def descargar_material(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/programas/<filename>')
def ver_pdf(filename):
    # Se unificó la descarga de programas y materiales desde static/material
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)