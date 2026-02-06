/**
 * Servicio para operaciones con orígenes de documentos.
 */
import api from './api'

/**
 * Servicio de orígenes con métodos CRUD y clasificación.
 */
export const originsService = {
  /**
   * Obtiene la lista de todos los orígenes.
   *
   * @param {boolean} includeInactive - Si incluir orígenes inactivos
   * @returns {Promise<{origins: Array}>}
   */
  async getAll(includeInactive = false) {
    const response = await api.get('/origins', {
      params: { include_inactive: includeInactive }
    })
    return response.data
  },

  /**
   * Obtiene un origen por su ID.
   *
   * @param {number} id - ID del origen
   * @returns {Promise<Object>}
   */
  async getById(id) {
    const response = await api.get(`/origins/${id}`)
    return response.data
  },

  /**
   * Crea un nuevo origen.
   *
   * @param {Object} data - Datos del origen
   * @param {string} data.codigo - Código único
   * @param {string} data.nombre - Nombre completo
   * @param {string} data.abreviacion - Abreviación
   * @param {string} data.color - Color hex (#RRGGBB)
   * @returns {Promise<Object>}
   */
  async create(data) {
    const response = await api.post('/origins', data)
    return response.data
  },

  /**
   * Actualiza un origen existente.
   *
   * @param {number} id - ID del origen
   * @param {Object} data - Datos a actualizar
   * @returns {Promise<Object>}
   */
  async update(id, data) {
    const response = await api.put(`/origins/${id}`, data)
    return response.data
  },

  /**
   * Elimina un origen.
   *
   * @param {number} id - ID del origen
   * @returns {Promise<Object>}
   */
  async delete(id) {
    const response = await api.delete(`/origins/${id}`)
    return response.data
  },

  /**
   * Clasifica una carátula usando IA.
   *
   * @param {string} caratula - Carátula a clasificar
   * @returns {Promise<{origen_codigo: string, origen_id: number}>}
   */
  async classifySingle(caratula) {
    const response = await api.post('/classify/single', { caratula })
    return response.data
  },

  /**
   * Clasifica múltiples carátulas usando IA.
   *
   * @param {Array<{id: any, caratula: string}>} items - Items a clasificar
   * @returns {Promise<{results: Array<{id: any, origen_codigo: string, origen_id: number}>}>}
   */
  async classifyBatch(items) {
    const response = await api.post('/classify/batch', { items })
    return response.data
  },

  /**
   * Extrae la carátula de un PDF sin procesarlo completamente.
   *
   * @param {File} file - Archivo PDF
   * @returns {Promise<{caratula: string|null, filename: string}>}
   */
  async extractCaratula(file) {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/ingest/extract-caratula', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })

    return response.data
  }
}

export default originsService
