"""
Modelos SQLAlchemy para la base de datos.

Principio SRP: Cada modelo representa una única entidad del dominio.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base


class Origen(Base):
    """
    Modelo para orígenes/categorías de documentos.

    Permite categorizar documentos por su fuente (tribunal, jurisdicción, etc.).

    Attributes:
        id: Identificador único del origen.
        codigo: Código corto único (ej: 'cfcp', 'csjn_civ').
        nombre: Nombre completo descriptivo.
        abreviacion: Abreviación para mostrar en UI.
        color: Color hexadecimal para identificación visual.
        activo: Si el origen está disponible para nuevos documentos.
        created_at: Fecha de creación.
    """
    __tablename__ = "origenes"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), unique=True, nullable=False)
    nombre = Column(String(255), nullable=False)
    abreviacion = Column(String(50), nullable=False)
    color = Column(String(7), nullable=False)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relación con documentos
    documents = relationship("Document", back_populates="origen")

    def __repr__(self):
        return f"<Origen(id={self.id}, codigo='{self.codigo}')>"


class Document(Base):
    """
    Modelo para documentos PDF subidos al sistema.
    
    Almacena metadatos del documento mientras el contenido
    vectorizado se guarda en ChromaDB.
    
    Attributes:
        id: Identificador único del documento.
        name: Nombre descriptivo del documento (del nombre de archivo).
        caratula: Carátula extraída del contenido del documento jurídico.
        search_content: Contenido procesado para búsqueda tradicional (nombres, códigos, materia, resumen).
        original_filename: Nombre original del archivo subido.
        file_path: Ruta al archivo PDF en el sistema de archivos.
        file_size: Tamaño del archivo en bytes.
        chunks_count: Cantidad de chunks creados en ChromaDB.
        created_at: Fecha y hora de creación.
        updated_at: Fecha y hora de última actualización.
    """
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    caratula = Column(String(500), nullable=True)  # Carátula extraída del PDF
    search_content = Column(Text, nullable=True)  # Contenido procesado para búsqueda tradicional
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=True)
    chunks_count = Column(Integer, default=0)
    origen_id = Column(Integer, ForeignKey('origenes.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación con origen
    origen = relationship("Origen", back_populates="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, name='{self.name}')>"
