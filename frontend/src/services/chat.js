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
   * @param {Array<{role: string, content: string}>} history - Historial de mensajes previos
   * @returns {Promise<{response: string, sources: Array<{text: string, score?: number}>}>}
   */
  async sendMessage(query, history = []) {
    const payload = { query }
    if (history.length > 0) {
      payload.history = history
    }
    const response = await api.post('/chat/', payload)
    return response.data
  }
}

export default chatService
