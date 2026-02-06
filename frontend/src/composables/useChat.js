/**
 * Composable para gestión del chat RAG.
 * 
 * Principio SRP: Este composable encapsula toda la lógica
 * relacionada con el chat (mensajes, envío, estados).
 */
import { ref, computed, nextTick } from 'vue'
import { chatService } from '@/services/chat'

/**
 * Composable que provee estado reactivo y operaciones para el chat.
 * 
 * @returns {Object} Estado y métodos para gestionar el chat
 */
export function useChat() {
  // Estado reactivo
  const messages = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Computed
  const hasMessages = computed(() => messages.value.length > 0)
  const lastMessage = computed(() => 
    messages.value.length > 0 ? messages.value[messages.value.length - 1] : null
  )

  // Counter para IDs únicos de mensajes
  let messageIdCounter = 0

  /**
   * Genera un ID único para un mensaje.
   * @returns {number}
   */
  function generateMessageId() {
    return ++messageIdCounter
  }

  /**
   * Envía un mensaje y recibe la respuesta del asistente.
   * 
   * @param {string} query - Texto del mensaje del usuario
   * @returns {Promise<Object|null>} Mensaje del asistente o null si hay error
   */
  async function sendMessage(query) {
    if (!query || !query.trim()) {
      return null
    }

    error.value = null
    
    // Agregar mensaje del usuario
    const userMessage = {
      id: generateMessageId(),
      role: 'user',
      content: query.trim()
    }
    messages.value.push(userMessage)
    
    // Indicar que está cargando
    loading.value = true
    
    try {
      // Enviar al backend
      const response = await chatService.sendMessage(query.trim())
      
      // Transformar sources del backend al formato del frontend
      // Usar la carátula del documento si está disponible
      const files = response.sources?.map((source, index) => ({
        id: source.document_id || index + 1,
        name: source.document_name || `Fuente ${index + 1}`,
        text: source.text,
        relevance: source.score ? Math.round(source.score * 100) : null,
        // Incluir document_id para poder abrir el preview
        documentId: source.document_id,
        // Incluir información del origen si existe
        origen: source.origen || null
      })) || []
      
      // Crear mensaje del asistente
      const assistantMessage = {
        id: generateMessageId(),
        role: 'assistant',
        content: response.response,
        files: files.length > 0 ? files : undefined
      }
      
      messages.value.push(assistantMessage)
      
      return assistantMessage
    } catch (err) {
      error.value = err.userMessage || 'Error al enviar mensaje'
      console.error('Error sending message:', err)
      
      // Agregar mensaje de error del sistema
      const errorMessage = {
        id: generateMessageId(),
        role: 'assistant',
        content: 'Lo siento, hubo un error al procesar tu consulta. Por favor, intenta nuevamente.',
        isError: true
      }
      messages.value.push(errorMessage)
      
      return null
    } finally {
      loading.value = false
    }
  }

  /**
   * Limpia todos los mensajes del chat.
   */
  function clearMessages() {
    messages.value = []
    error.value = null
    messageIdCounter = 0
  }

  /**
   * Limpia el error actual.
   */
  function clearError() {
    error.value = null
  }

  /**
   * Elimina un mensaje específico por ID.
   * 
   * @param {number} id - ID del mensaje a eliminar
   */
  function removeMessage(id) {
    messages.value = messages.value.filter(msg => msg.id !== id)
  }

  return {
    // Estado
    messages,
    loading,
    error,
    
    // Computed
    hasMessages,
    lastMessage,
    
    // Métodos
    sendMessage,
    clearMessages,
    clearError,
    removeMessage
  }
}

export default useChat
