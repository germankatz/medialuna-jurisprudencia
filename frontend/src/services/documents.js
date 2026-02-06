/**
 * Servicio para operaciones con documentos.
 * 
 * Principio ISP: Interfaz específica para operaciones de documentos,
 * separada del servicio de chat.
 */
import api from './api'

/**
 * Servicio de documentos con métodos CRUD y upload.
 */
export const documentsService = {
  /**
   * Obtiene la lista de todos los documentos.
   * 
   * @param {Object} options - Opciones de paginación
   * @param {number} options.skip - Documentos a saltar (offset)
   * @param {number} options.limit - Máximo de documentos a retornar
   * @returns {Promise<{documents: Array, total: number}>}
   */
  async getAll({ skip = 0, limit = 100 } = {}) {
    const response = await api.get('/documents', {
      params: { skip, limit }
    })
    return response.data
  },

  /**
   * Obtiene un documento por su ID.
   * 
   * @param {number} id - ID del documento
   * @returns {Promise<Object>} Datos del documento
   */
  async getById(id) {
    const response = await api.get(`/documents/${id}`)
    return response.data
  },

  /**
   * Sube un archivo PDF al servidor.
   *
   * @param {File} file - Archivo PDF a subir
   * @param {Function} onProgress - Callback para progreso de subida (0-100)
   * @param {number|null} origenId - ID del origen/categoría del documento
   * @returns {Promise<{id: number, filename: string, status: string, chunks_created: number}>}
   */
  async upload(file, onProgress = null, origenId = null) {
    const formData = new FormData()
    formData.append('file', file)
    if (origenId !== null && origenId !== 'auto') {
      formData.append('origen_id', origenId)
    }

    const response = await api.post('/ingest/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      }
    })

    return response.data
  },

  /**
   * Elimina un documento por su ID.
   * 
   * @param {number} id - ID del documento a eliminar
   * @returns {Promise<{message: string, id: number}>}
   */
  async delete(id) {
    const response = await api.delete(`/documents/${id}`)
    return response.data
  },

  /**
   * Descarga un documento PDF.
   * 
   * @param {number} id - ID del documento
   * @param {string} filename - Nombre para el archivo descargado
   */
  async download(id, filename) {
    const response = await api.get(`/documents/${id}/download`, {
      responseType: 'blob'
    })
    
    // Crear enlace de descarga
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename || 'documento.pdf')
    document.body.appendChild(link)
    link.click()
    
    // Limpiar
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  /**
   * Obtiene la URL para previsualizar un documento (inline).
   * 
   * @param {number} id - ID del documento
   * @returns {string} URL de preview del documento
   */
  getPreviewUrl(id) {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
    return `${baseUrl}/documents/${id}/preview`
  },

  /**
   * Busca documentos por texto en nombre, carátula y contenido.
   * Búsqueda tradicional (no usa LLM).
   *
   * @param {string} query - Texto a buscar (mínimo 2 caracteres)
   * @param {Object} options - Opciones de paginación y filtros
   * @param {number} options.skip - Documentos a saltar (offset)
   * @param {number} options.limit - Máximo de documentos a retornar
   * @param {number|null} options.origenId - ID del origen para filtrar (opcional)
   * @returns {Promise<{documents: Array, total: number}>}
   */
  async search(query, { skip = 0, limit = 20, origenId = null } = {}) {
    const params = { q: query, skip, limit }
    if (origenId !== null) {
      params.origen_id = origenId
    }
    const response = await api.get('/documents/search', { params })
    return response.data
  },

  /**
   * Actualiza el origen de un documento.
   *
   * @param {number} id - ID del documento
   * @param {number} origenId - ID del nuevo origen
   * @returns {Promise<Object>} Documento actualizado
   */
  async updateOrigen(id, origenId) {
    const response = await api.put(`/documents/${id}/origen`, {
      origen_id: origenId
    })
    return response.data
  }
}

export default documentsService
