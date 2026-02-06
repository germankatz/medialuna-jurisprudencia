/**
 * Composable para gestión de documentos.
 * 
 * Principio SRP: Este composable encapsula toda la lógica
 * relacionada con documentos (estado, operaciones, errores).
 */
import { ref, computed } from 'vue'
import { documentsService } from '@/services/documents'

// Contador para generar IDs únicos para archivos en cola
let queueIdCounter = 0

// Tamaño de página para carga de documentos
const PAGE_SIZE = 50

/**
 * Composable que provee estado reactivo y operaciones para documentos.
 * 
 * @returns {Object} Estado y métodos para gestionar documentos
 */
export function useDocuments() {
  // Estado reactivo
  const documents = ref([])
  const loading = ref(false)
  const loadingMore = ref(false)
  const error = ref(null)
  const uploadProgress = ref(0)
  const isUploading = ref(false)
  
  // Estado de paginación
  const currentPage = ref(0)
  const total = ref(0)
  const hasMore = computed(() => documents.value.length < total.value)
  
  // Estado de cola de subida
  // Estructura: { id, file, name, size, status: 'pending'|'uploading'|'success'|'error', error?, progress?, origen?, caratula?, caratulaLoading? }
  const pendingFiles = ref([])
  const isProcessingQueue = ref(false)

  // Computed
  const hasDocuments = computed(() => documents.value.length > 0)
  const totalDocuments = computed(() => total.value)
  
  // Computed para la cola
  const hasPendingFiles = computed(() => pendingFiles.value.length > 0)
  const pendingCount = computed(() => 
    pendingFiles.value.filter(f => f.status === 'pending').length
  )
  const canProcessQueue = computed(() => 
    pendingCount.value > 0 && !isProcessingQueue.value
  )

  /**
   * Carga la lista inicial de documentos desde el servidor.
   * Resetea la paginación al inicio.
   */
  async function fetchDocuments() {
    loading.value = true
    error.value = null
    currentPage.value = 0
    
    try {
      const response = await documentsService.getAll({ 
        skip: 0, 
        limit: PAGE_SIZE 
      })
      documents.value = response.documents
      total.value = response.total
    } catch (err) {
      error.value = err.userMessage || 'Error al cargar documentos'
      console.error('Error fetching documents:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * Carga más documentos (scroll infinito).
   * Se usa cuando el usuario hace scroll hacia abajo.
   */
  async function loadMoreDocuments() {
    if (loadingMore.value || !hasMore.value || loading.value) return
    
    loadingMore.value = true
    currentPage.value++
    
    try {
      const response = await documentsService.getAll({
        skip: currentPage.value * PAGE_SIZE,
        limit: PAGE_SIZE
      })
      documents.value = [...documents.value, ...response.documents]
    } catch (err) {
      // Revertir el incremento de página en caso de error
      currentPage.value--
      console.error('Error cargando más documentos:', err)
    } finally {
      loadingMore.value = false
    }
  }

  /**
   * Sube un nuevo documento.
   * 
   * @param {File} file - Archivo PDF a subir
   * @returns {Promise<Object|null>} Documento creado o null si hay error
   */
  async function uploadDocument(file) {
    isUploading.value = true
    uploadProgress.value = 0
    error.value = null
    
    try {
      const result = await documentsService.upload(file, (progress) => {
        uploadProgress.value = progress
      })
      
      // Intentar obtener el documento completo (incluye origen)
      let newDoc = null
      try {
        newDoc = await documentsService.getById(result.id)
      } catch (fetchErr) {
        console.warn('No se pudo obtener el documento completo tras upload:', fetchErr)
      }

      if (!newDoc) {
        // Fallback si la consulta falla
        newDoc = {
          id: result.id,
          name: file.name.replace('.pdf', ''),
          original_filename: result.filename,
          file_size: file.size,
          chunks_count: result.chunks_created,
          created_at: new Date().toISOString(),
          origen: null
        }
      }
      
      documents.value = [newDoc, ...documents.value]
      total.value++ // Incrementar el total
      
      return result
    } catch (err) {
      error.value = err.userMessage || 'Error al subir documento'
      console.error('Error uploading document:', err)
      return null
    } finally {
      isUploading.value = false
      uploadProgress.value = 0
    }
  }

  /**
   * Elimina un documento por su ID.
   * 
   * @param {number} id - ID del documento a eliminar
   * @returns {Promise<boolean>} true si se eliminó correctamente
   */
  async function deleteDocument(id) {
    error.value = null
    
    try {
      await documentsService.delete(id)
      // Remover de la lista local
      documents.value = documents.value.filter(doc => doc.id !== id)
      total.value-- // Decrementar el total
      return true
    } catch (err) {
      error.value = err.userMessage || 'Error al eliminar documento'
      console.error('Error deleting document:', err)
      return false
    }
  }

  /**
   * Descarga un documento.
   * 
   * @param {number} id - ID del documento
   * @param {string} filename - Nombre del archivo
   */
  async function downloadDocument(id, filename) {
    try {
      await documentsService.download(id, filename)
    } catch (err) {
      error.value = err.userMessage || 'Error al descargar documento'
      console.error('Error downloading document:', err)
    }
  }

  /**
   * Obtiene la URL de preview de un documento.
   * 
   * @param {number} id - ID del documento
   * @returns {string} URL de preview
   */
  function getPreviewUrl(id) {
    return documentsService.getPreviewUrl(id)
  }

  /**
   * Limpia el error actual.
   */
  function clearError() {
    error.value = null
  }

  // ==========================================
  // Métodos de cola de subida
  // ==========================================

  /**
   * Agrega archivos a la cola de subida.
   *
   * @param {File[]} files - Array de archivos a agregar
   * @param {number|string|null} defaultOrigen - Origen por defecto ('auto', id, o null)
   */
  function addFilesToQueue(files, defaultOrigen = null) {
    const newFiles = files.map(file => ({
      id: ++queueIdCounter,
      file,
      name: file.name,
      size: file.size,
      status: 'pending',
      error: null,
      progress: 0,
      origen: defaultOrigen,
      caratula: null,
      caratulaLoading: false
    }))

    pendingFiles.value = [...pendingFiles.value, ...newFiles]
  }

  /**
   * Actualiza el origen de un archivo en la cola.
   *
   * @param {number} id - ID del archivo en la cola
   * @param {number|string|null} origen - Nuevo origen
   */
  function updateFileOrigen(id, origen) {
    const index = pendingFiles.value.findIndex(f => f.id === id)
    if (index !== -1) {
      pendingFiles.value[index] = {
        ...pendingFiles.value[index],
        origen
      }
    }
  }

  /**
   * Actualiza la carátula de un archivo en la cola.
   *
   * @param {number} id - ID del archivo en la cola
   * @param {string|null} caratula - Nueva carátula
   */
  function updateFileCaratula(id, caratula) {
    const index = pendingFiles.value.findIndex(f => f.id === id)
    if (index !== -1) {
      pendingFiles.value[index] = {
        ...pendingFiles.value[index],
        caratula,
        caratulaLoading: false
      }
    }
  }

  /**
   * Marca un archivo como cargando carátula.
   *
   * @param {number} id - ID del archivo en la cola
   * @param {boolean} loading - Estado de carga
   */
  function setFileCaratulaLoading(id, loading) {
    const index = pendingFiles.value.findIndex(f => f.id === id)
    if (index !== -1) {
      pendingFiles.value[index] = {
        ...pendingFiles.value[index],
        caratulaLoading: loading
      }
    }
  }

  /**
   * Elimina un archivo de la cola.
   * 
   * @param {number} id - ID del archivo en la cola
   */
  function removeFromQueue(id) {
    pendingFiles.value = pendingFiles.value.filter(f => f.id !== id)
  }

  /**
   * Limpia toda la cola (solo archivos pendientes o con error).
   */
  function clearQueue() {
    pendingFiles.value = pendingFiles.value.filter(
      f => f.status === 'uploading' || f.status === 'success'
    )
  }

  /**
   * Limpia los archivos completados de la cola.
   */
  function clearCompletedFromQueue() {
    pendingFiles.value = pendingFiles.value.filter(
      f => f.status !== 'success'
    )
  }

  /**
   * Procesa todos los archivos pendientes en la cola.
   */
  async function processQueue() {
    if (isProcessingQueue.value) return
    
    isProcessingQueue.value = true
    error.value = null
    
    // Obtener solo archivos pendientes
    const filesToProcess = pendingFiles.value.filter(f => f.status === 'pending')
    
    for (const queueItem of filesToProcess) {
      // Actualizar estado a 'uploading'
      const index = pendingFiles.value.findIndex(f => f.id === queueItem.id)
      if (index === -1) continue // El archivo fue removido
      
      pendingFiles.value[index] = {
        ...pendingFiles.value[index],
        status: 'uploading',
        progress: 0
      }
      
      try {
        // Obtener origen_id (si es 'auto' o null, no enviamos origen)
        const origenId = queueItem.origen && queueItem.origen !== 'auto'
          ? queueItem.origen
          : null

        const result = await documentsService.upload(queueItem.file, (progress) => {
          // Actualizar progreso individual
          const idx = pendingFiles.value.findIndex(f => f.id === queueItem.id)
          if (idx !== -1) {
            pendingFiles.value[idx] = {
              ...pendingFiles.value[idx],
              progress
            }
          }
        }, origenId)
        
        // Marcar como éxito y liberar referencia al File para permitir garbage collection
        const successIndex = pendingFiles.value.findIndex(f => f.id === queueItem.id)
        if (successIndex !== -1) {
          pendingFiles.value[successIndex] = {
            ...pendingFiles.value[successIndex],
            status: 'success',
            progress: 100,
            file: null // Liberar memoria del Blob
          }
        }
        
        // Agregar el nuevo documento a la lista (con origen si está disponible)
        let newDoc = null
        try {
          newDoc = await documentsService.getById(result.id)
        } catch (fetchErr) {
          console.warn('No se pudo obtener el documento completo tras upload:', fetchErr)
        }

        if (!newDoc) {
          newDoc = {
            id: result.id,
            name: queueItem.name.replace('.pdf', ''),
            original_filename: result.filename,
            file_size: queueItem.size,
            chunks_count: result.chunks_created,
            created_at: new Date().toISOString(),
            origen: null
          }
        }
        
        documents.value = [newDoc, ...documents.value]
        total.value++ // Incrementar el total
        
      } catch (err) {
        // Marcar como error
        const errorIndex = pendingFiles.value.findIndex(f => f.id === queueItem.id)
        if (errorIndex !== -1) {
          pendingFiles.value[errorIndex] = {
            ...pendingFiles.value[errorIndex],
            status: 'error',
            error: err.userMessage || 'Error al subir archivo',
            progress: 0
          }
        }
        console.error(`Error uploading ${queueItem.name}:`, err)
      }
    }
    
    isProcessingQueue.value = false
  }

  /**
   * Reintenta subir un archivo con error.
   * 
   * @param {number} id - ID del archivo en la cola
   */
  function retryFile(id) {
    const index = pendingFiles.value.findIndex(f => f.id === id)
    if (index !== -1 && pendingFiles.value[index].status === 'error') {
      pendingFiles.value[index] = {
        ...pendingFiles.value[index],
        status: 'pending',
        error: null,
        progress: 0
      }
    }
  }

  return {
    // Estado
    documents,
    loading,
    loadingMore,
    error,
    uploadProgress,
    isUploading,
    
    // Estado de paginación
    total,
    hasMore,
    
    // Estado de cola
    pendingFiles,
    isProcessingQueue,
    
    // Computed
    hasDocuments,
    totalDocuments,
    hasPendingFiles,
    pendingCount,
    canProcessQueue,
    
    // Métodos
    fetchDocuments,
    loadMoreDocuments,
    uploadDocument,
    deleteDocument,
    downloadDocument,
    getPreviewUrl,
    clearError,
    
    // Métodos de cola
    addFilesToQueue,
    removeFromQueue,
    clearQueue,
    clearCompletedFromQueue,
    processQueue,
    retryFile,
    updateFileOrigen,
    updateFileCaratula,
    setFileCaratulaLoading
  }
}

export default useDocuments
