from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from keycloak import KeycloakOpenID
import pyodbc 
from django.contrib.auth.models import User
from datetime import datetime
import pytz

#Importar conexión a DB
import portal.clases.conexionDB as conexionDB

#Importar Modelo de DB Users
from users.models import Log_Usuario


LEGACY_AGRISTATS_PRODUCT_USERS = {
    'pollos': {
        'wrodriguez', 'gromo', 'damarquc', 'tvgarcin', 'hmaggiori', 'aespinosa',
        'cdeleon', 'eagudelo', 'sdeleon', 'jfaguirl', 'mpcrespb', 'jmejia',
        'ialmeida', 'jzambrano', 'gcoronado', 'mmosquera', 'jromero', 'jrugeles',
        'dpila', 'dchaves', 'vcastellanos', 'eparedes', 'nrhea', 'lpaez',
        'gnromerog', 'falvarado', 'lesanchezc', 'scepeda', 'jegrandac',
        'alzuritr', 'ensalazd', 'hvelasco', 'alara', 'jafiallh', 'jochoa',
        'fvvillalvav', 'fnarvaez', 'mgvargav', 'wyepez'
    },
    'cerdos': {
        'wrodriguez', 'gromo', 'damarquc', 'tvgarcin', 'hmaggiori', 'aespinosa',
        'cdeleon', 'eagudelo', 'sdeleon', 'mpcrespb', 'jfaguirl', 'jmejia',
        'ialmeida', 'msalgado', 'fjacome', 'jatroyam', 'fjaramillo',
        'vcaizaluisa', 'ymantambac', 'falvarado', 'scepeda', 'oaguirre',
        'jegrandac', 'alzuritr', 'ensalazd', 'jafiallh', 'mgvargav', 'wyepez',
        'wmvegam', 'hvalarezo', 'hvelasco', 'alara'
    }
}


####################################
## Agregar datos al log de usuario #
####################################
def log_usuario(user,tarea):        
    fecha_ecuador = datetime.now()    

    log = Log_Usuario(usuario=user,fecha_actividad=fecha_ecuador,actividad=tarea)
    log.save()

######################################
###### Validar usuario en Keycloak ###
######################################
def login_keycloak(usuario,password):
    try:
        '''
        keycloak_openid = KeycloakOpenID(server_url="",
                        client_id="sip",
                        realm_name="pronaca-gb")    
                        '''
        keycloak_openid = KeycloakOpenID(server_url="https://cdkcpro.pronaca.com/auth/",
                        client_id="sip",
                        realm_name="pronaca-gb")                
        token = keycloak_openid.token(usuario,password)
        userinfo = keycloak_openid.userinfo(token['access_token'])
        nombreUsuario = userinfo['preferred_username']
        email = userinfo['email']
        nombre = userinfo['given_name']
        apellido = userinfo['family_name']        
        autenticacionK = 'valido'
    except Exception as e:
        autenticacionK = 'invalido'
        nombreUsuario = ''
        email = ''
        nombre = ''
        apellido = ''
    return nombreUsuario,email,nombre,apellido,autenticacionK

#########################
##### Login Portal ######
#########################
def login_portal(request):
    if request.method == 'POST':
        usuario = request.POST['username']
        psw = request.POST['password']
        esEmail = usuario.rfind('@')

        #Validar si lo ingresado no es correo
        if esEmail == -1:
            nombreUsuario,email,nombre,apellido,autenticacionK = login_keycloak(usuario,psw)

            #conusltar si usuario existe en base de datos
            conexion = conexionDB.conexionDB('PortalPecuario')
            cursor = conexion.cursor()
            queryConsulta = '''
                            declare @usuario nvarchar(64) = ?
                            select count(*) as CantidadUsuario from auth_user where username = @usuario or email = @usuario                        
                            '''
            cursor.execute(queryConsulta,usuario)
            resultado = cursor.fetchone()

            #Validar que el usuario exista para crearlo o actualizarlo
            if resultado.CantidadUsuario == 0:
                #Si usuario es nuevo, validar que exista en keycloak y la contraseña sea correcta
                if autenticacionK == 'valido':
                    #Agregar usuario a Django
                    usarioDjango = User.objects.create_user(nombreUsuario,email,psw)                
                    usarioDjango.first_name = nombre
                    usarioDjango.last_name = apellido
                    usarioDjango.save()

                    #Iniciar sesion en Portal
                    user = authenticate(request,username=usuario, password=psw)
                    if user is not None:                
                        login(request,user)                
                        #Inicializar variable de contraseña
                        psw = ''
                        log_usuario(usuario,'Autenticacion')      
                        return redirect('/')
                    else:                    
                        return render(request,'users/login.html',{'error':'Usuario o Contraseña Incorrectos!!!'}) 
                else:
                    return render(request,'users/login.html',{'error':'Usuario o Contraseña Incorrectos!!!'})
            else:             
                #validar que usuario exista en keycloak y la contraseña sea correcta
                if autenticacionK == 'valido':                    
                    u = User.objects.get(username=usuario)

                    #validar que no sea super user de Django
                    if u.username != 'sipUser':

                        #validar que haya cambiado de contraseña
                        if u.check_password(psw):                                                
                            #Iniciar Sesion
                            user = authenticate(request, username=usuario, password=psw)                                        
                        else:                             
                            #validar cambio de contraseña
                            u.set_password(psw)
                            u.save()
                            
                            #Iniciar Sesion
                            user = authenticate(request, username=usuario, password=psw)            
                            
                        if user is not None:
                            usuario = request.user                
                            context = {'usuario':user}            
                            login(request,user)     
                            psw = '' #inicializar variables     
                            log_usuario(usuario,'Autenticacion')      
                            return redirect('/')
                        else:                                
                            return render(request,'users/login.html',{'error':'Usuario o Contraseña Incorrectos!!!'}) 
                    else:                 
                        #Iniciar Sesion
                        user = authenticate(request, username=usuario, password=psw)            
                        if user is not None:                
                            login(request,user)  
                            print(login(request,user))              
                            return redirect('/')
                        else:                            
                            return render(request,'users/login.html',{'error':'Usuario o Contraseña Incorrectos!!!'})
                else:
                    return render(request,'users/login.html',{'error':'Usuario o Contraseña Incorrectos!!!'}) 
        else: 
            return render(request,'users/login.html',{'errorMail':'No ingrese su usuario con @'}) 
                                                    
    return render(request,'users/login.html')
    

    
@login_required
def logout_portal(request):
    user = request.user
    log_usuario(user,'Salir del Aplicativo')      
    logout(request)
    return redirect('login')


def validarAcceso(usuario,aplicacion,negocio):        
    conexion = conexionDB.conexionDB('PortalPecuario')
    cursor = conexion.cursor()    
    queryConsulta = '''    
    declare @aplicacion nvarchar(256) = ?
    declare @usuario nvarchar(256) = ?
    declare @negocio nvarchar(128) = ?
    select count(sa.IdUsuario) as NumeroPermisos
	from auth_user u
		join sipAcceso sa on u.id = sa.IdUsuario
		join sipAplicacion app on sa.IdAplicacion = app.IdAplicacion
	where app.Aplicacion = @aplicacion
		and u.username = @usuario
		and sa.EstadoAcceso = 1
        and app.Negocio = @negocio
    '''              
    cursor.execute(queryConsulta,aplicacion,str(usuario),negocio)    
    acceso = cursor.fetchone()    
    return acceso[0]    


def has_portal_permission(user, permission_code, fallback_aplicacion=None, fallback_negocio=None):
    """
    Evalua permisos Django y, opcionalmente, aplica fallback temporal a la validacion legacy.
    """
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    if user.has_perm(permission_code):
        return True

    if fallback_aplicacion and fallback_negocio and getattr(settings, 'USE_LEGACY_ACCESS_FALLBACK', True):
        try:
            return validarAcceso(user, fallback_aplicacion, fallback_negocio) >= 1
        except Exception:
            return False

    return False


def has_agristats_product_access(user, product):
    """
    Transicion de Agristats por producto:
    1) permiso Django
    2) grupo funcional
    3) allowlist legacy (temporal)
    """
    product_key = (product or '').strip().lower()
    permission_map = {
        'pollos': 'portal.download_agristats_pollos',
        'cerdos': 'portal.download_agristats_cerdos',
    }
    group_map = {
        'pollos': 'Agristats_Pollos',
        'cerdos': 'Agristats_Cerdos',
    }

    permission_code = permission_map.get(product_key)
    if permission_code and has_portal_permission(user, permission_code):
        return True

    group_name = group_map.get(product_key)
    if group_name and user.groups.filter(name=group_name).exists():
        return True

    if getattr(settings, 'USE_LEGACY_AGRISTATS_ALLOWLIST', True):
        return str(user) in LEGACY_AGRISTATS_PRODUCT_USERS.get(product_key, set())

    return False

