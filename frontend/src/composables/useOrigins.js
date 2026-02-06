/**
 * Composable para gestión de orígenes de documentos.
 */
import { ref, computed } from 'vue'
import { originsService } from '@/services/origins'

/**
 * Composable que provee estado reactivo y operaciones para orígenes.
 *
 * @returns {Object} Estado y métodos para gestionar orígenes
 */
export function useOrigins() {
  // Estado reactivo
  const origins = ref([])
  const loading = ref(false)
  const error = ref(null)
  const isClassifying = ref(false)
  const classifyingProgress = ref({ current: 0, total: 0 })

  // Computed
  const hasOrigins = computed(() => origins.value.length > 0)

  /**
   * Obtiene un origen por su código.
   *
   * @param {string} codigo - Código del origen
   * @returns {Object|null} Origen encontrado o null
   */
  function getOrigenByCodigo(codigo) {
    return origins.value.find(o => o.codigo === codigo) || null
  }

  /**
   * Obtiene un origen por su ID.
   *
   * @param {number} id - ID del origen
   * @returns {Object|null} Origen encontrado o null
   */
  function getOrigenById(id) {
    return origins.value.find(o => o.id === id) || null
  }

  /**
   * Carga la lista de orígenes desde el servidor.
   */
  async function fetchOrigins() {
    loading.value = true
    error.value = null

    try {
      const response = await originsService.getAll()
      origins.value = response.origins
    } catch (err) {
      error.value = err.userMessage || 'Error al cargar orígenes'
      console.error('Error fetching origins:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * Clasifica una carátula usando IA.
   *
   * @param {string} caratula - Carátula a clasificar
   * @returns {Promise<{origen_codigo: string, origen_id: number}|null>}
   */
  async function classifySingle(caratula) {
    if (!caratula) return null

    try {
      return await originsService.classifySingle(caratula)
    } catch (err) {
      console.error('Error classifying:', err)
      return null
    }
  }

  /**
   * Clasifica múltiples carátulas usando IA.
   *
   * @param {Array<{id: any, caratula: string}>} items - Items a clasificar
   * @returns {Promise<Array<{id: any, origen_codigo: string, origen_id: number}>>}
   */
  async function classifyBatch(items) {
    if (!items || items.length === 0) return []

    isClassifying.value = true
    error.value = null

    try {
      const response = await originsService.classifyBatch(items)
      return response.results
    } catch (err) {
      error.value = err.userMessage || 'Error al clasificar documentos'
      console.error('Error batch classifying:', err)
      return []
    } finally {
      isClassifying.value = false
    }
  }

  /**
   * Clasifica múltiples carátulas una por una, actualizando progreso en tiempo real.
   *
   * @param {Array<{id: any, caratula: string}>} items - Items a clasificar
   * @param {Function} onProgress - Callback llamado después de cada clasificación (result, current, total)
   * @returns {Promise<Array<{id: any, origen_codigo: string, origen_id: number}>>}
   */
  async function classifyOneByOne(items, onProgress) {
    if (!items || items.length === 0) return []

    isClassifying.value = true
    classifyingProgress.value = { current: 0, total: items.length }
    error.value = null
    const results = []

    try {
      for (let i = 0; i < items.length; i++) {
        const item = items[i]

        try {
          // Clasificar individualmente
          const result = await originsService.classifySingle(item.caratula)
          const fullResult = {
            id: item.id,
            origen_codigo: result.origen_codigo,
            origen_id: result.origen_id
          }

          results.push(fullResult)

          // Actualizar progreso
          classifyingProgress.value.current = i + 1

          // Llamar al callback con el resultado y progreso
          if (onProgress && typeof onProgress === 'function') {
            onProgress(fullResult, i + 1, items.length)
          }
        } catch (err) {
          console.error(`Error classifying item ${item.id}:`, err)
          // Si falla uno, continuar con los demás
        }
      }

      return results
    } catch (err) {
      error.value = err.userMessage || 'Error al clasificar documentos'
      console.error('Error in classifyOneByOne:', err)
      return results
    } finally {
      isClassifying.value = false
      classifyingProgress.value = { current: 0, total: 0 }
    }
  }

  /**
   * Extrae la carátula de un archivo PDF.
   *
   * @param {File} file - Archivo PDF
   * @returns {Promise<string|null>} Carátula extraída o null
   */
  async function extractCaratula(file) {
    try {
      const response = await originsService.extractCaratula(file)
      return response.caratula
    } catch (err) {
      console.error('Error extracting caratula:', err)
      return null
    }
  }

  return {
    // Estado
    origins,
    loading,
    error,
    isClassifying,
    classifyingProgress,

    // Computed
    hasOrigins,

    // Métodos
    fetchOrigins,
    getOrigenByCodigo,
    getOrigenById,
    classifySingle,
    classifyBatch,
    classifyOneByOne,
    extractCaratula
  }
}

export default useOrigins
