import os
from fastapi import FastAPI,HTTPException, status
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from bson.objectid import ObjectId
from pymongo import MongoClient
from pydantic import BaseModel, Field
from datetime import date
from dotenv import load_dotenv
load_dotenv()

# Acceder a las variables de entorno
mongo_uri = os.getenv('MONGO_URI')
db_name = os.getenv('DB_NAME')
collection_name = os.getenv('COLLECTION_NAME')

# Conectar a MongoDB
client = MongoClient(mongo_uri)
db = client[db_name]
collection = db[collection_name]

app = FastAPI()
# Configurar el middleware de CORS para permitir cualquier origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir cualquier origen
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Permitir todos los métodos HTTP
    allow_headers=["*"],  # Permitir todos los encabezados
)

# modelo de datos 
class Producto(BaseModel):
    nombre: str
    cantidad: str
    precio: float= Field(default=0.0)

class Compra(BaseModel):
    fecha: date = Field(default_factory=lambda: str(date.today()))
    productos: list[Producto] = Field(default_factory=list)
    total: float = Field(default=0.0)
    numProductos: int = Field(default=0)
    

# FUNCION PARA TRAER LOS REGISTROS DE COMPRAS 
@app.get("/", status_code=200)
async def root():
    try:     
        cursor = collection.find()
        compras = []
        for compra in cursor:
            compra["_id"] = str(compra["_id"])
            # Ordenar los productos por su campo 'id'
            compra['productos'].sort(key=lambda prod: prod.get('id', 0))
            compras.insert(0,compra)
        return compras
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# FUNCION PARA REGISTRAR COMRPAS
@app.post("/compras", status_code=201)
async def crear_compra(compra: Compra):
    try:
        compra_dict = compra.dict()
        compra_dict["_id"] = ObjectId()
        result_compra = collection.insert_one(compra_dict)
        if not result_compra.inserted_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al registrar la compra")
        return {"mensaje": "Compra registrada correctamente", "id_compra": str(compra_dict["_id"])}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        

# FUNCION PARA REGISTRAR PRODCUTOS EN UNA COMPRA
@app.post("/compras/{id_compra}/productos", status_code=201)
async def registrar_producto(id_compra: str, producto: Producto):
    try:
        # Convertir el ID de compra a ObjectId
        compra_obj_id = ObjectId(id_compra)
        
        # Verificar si la compra existe
        compra_actual = collection.find_one({"_id": compra_obj_id})
        if not compra_actual:
            raise HTTPException(status_code=404, detail="No se encontró la compra con el ID proporcionado")
        
        # Obtener la lista de productos
        productos = compra_actual.get("productos", [])
        
        # Generar el ID del producto
        if len(productos) == 0:
            # Si no hay productos registrados aún, empezamos desde el ID 1
            producto_id = 1
        else:
            # Obtener el último ID de producto y sumar 1 para el nuevo producto
            ultimo_id = max(prod["id"] for prod in productos)
            producto_id = ultimo_id + 1
        
        # Agregar el ID del producto al objeto del producto
        producto_dict = producto.dict()
        producto_dict["id"] = producto_id
        
        # Actualizar la compra con el nuevo producto
        result = collection.update_one(
            {"_id": compra_obj_id},
            {"$addToSet": {"productos": producto_dict}}
        )
        
        # Verificar si se modificó correctamente la compra
        if result.modified_count == 1:
            # Actualizar el total y número de productos en la compra
            compra_actualizada = collection.find_one({"_id": compra_obj_id})
            nuevo_total = sum(prod['precio'] for prod in compra_actualizada['productos'])
            nuevo_num_productos = len(compra_actualizada['productos'])
            collection.update_one(
                {"_id": compra_obj_id},
                {"$set": {"total": nuevo_total, "numProductos": nuevo_num_productos}}
            )
            return {"mensaje": "Producto registrado correctamente", "producto": producto_dict}
        else:
            raise HTTPException(status_code=404, detail="No se encontró la compra con el ID proporcionado")
    
    except HTTPException as e:
        raise e
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    except HTTPException as e:
        raise e
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# FUNCION PARA ELIMINAR UNA COMPRA 
@app.delete("/{id}", status_code=200)
async def delete(id):
    try:
        obj_id = ObjectId(id)
        result = collection.delete_one({"_id": obj_id})
        if result.deleted_count == 1:
            return {"mensaje": "Compra eliminada correctamente"}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró la compra con el ID proporcionado")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    


# FUNCION PARA ELIMINAR UN PRODUCTO EN ESPECIFICO DE UNA COMPRA 
@app.delete("/compra/{compra_id}/producto/{producto_id}", status_code=200)
async def delete_producto(compra_id: str, producto_id: int):
    try:
        compra_obj_id = ObjectId(compra_id)
        producto_obj_id = producto_id
        result = collection.update_one(
            {"_id": compra_obj_id},
            {"$pull": {"productos": {"id": producto_obj_id}}}
        )    
        if result.modified_count == 1:
            compra_actualizada = collection.find_one({"_id": compra_obj_id})
            nuevo_total = sum(producto['precio'] for producto in compra_actualizada['productos'])
            nuevo_num_productos = len(compra_actualizada['productos'])
            collection.update_one(
                {"_id": compra_obj_id},
                {"$set": {"total": nuevo_total, "numProductos": nuevo_num_productos}}
            )     
            return {"mensaje": "Producto eliminado correctamente"}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el producto con el ID proporcionado en la compra")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))