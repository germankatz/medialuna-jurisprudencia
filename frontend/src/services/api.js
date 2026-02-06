/**
 * Configuración base de Axios para comunicación con el backend.
 * 
 * Principio SRP: Este módulo solo se encarga de la configuración
 * y manejo de errores de las peticiones HTTP.
 */
import axios from 'axios'

// URL base del API (configurable por variable de entorno)
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// Instancia de Axios configurada
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutos para operaciones largas como procesamiento de PDFs
  headers: {
    'Content-Type': 'application/json'
  }
})

// Interceptor de request (para logging o auth en el futuro)
api.interceptors.request.use(
  (config) => {
    // Aquí se puede agregar token de autenticación en el futuro
    // config.headers.Authorization = `Bearer ${token}`
    return config
  },
  (error) => {
    console.error('Error en request:', error)
    return Promise.reject(error)
  }
)

// Interceptor de response (manejo centralizado de errores)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Extraer mensaje de error del backend
    let errorMessage = 'Error de conexión con el servidor'
    
    if (error.response) {
      // El servidor respondió con un código de error
      const { status, data } = error.response
      
      switch (status) {
        case 400:
          errorMessage = data.detail || 'Datos inválidos'
          break
        case 404:
          errorMessage = data.detail || 'Recurso no encontrado'
          break
        case 500:
          errorMessage = data.detail || 'Error interno del servidor'
          break
        default:
          errorMessage = data.detail || `Error ${status}`
      }
    } else if (error.request) {
      // No se recibió respuesta
      errorMessage = 'No se pudo conectar con el servidor'
    }
    
    // Agregar mensaje procesado al error
    error.userMessage = errorMessage
    
    return Promise.reject(error)
  }
)

export default api
