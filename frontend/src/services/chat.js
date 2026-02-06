/**
 * Servicio para operaciones de chat RAG.
 * 
 * Principio ISP: Interfaz específica para operaciones de chat,
 * separada del servicio de documentos.
 */
import api from './api'

/**
 * Servicio de chat con el asistente RAG.
 */
export const chatService = {
  /**
   * Envía un mensaje al asistente y recibe una respuesta.
   * 
   * La respuesta incluye el texto generado y las fuentes relevantes
   * de la jurisprudencia indexada.
   * 
   * @param {string} query - Pregunta o consulta del usuario
   * @returns {Promise<{response: string, sources: Array<{text: string, score?: number}>}>}
   */
  async sendMessage(query) {
    const response = await api.post('/chat/', { query })
    return response.data
  }
}

export default chatService
