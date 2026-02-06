<script setup>
import { ref, onMounted, computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Plus,
  Pencil,
  Trash2,
  Loader2,
  Tag,
  Check,
  X,
  AlertCircle
} from 'lucide-vue-next'
import { originsService } from '@/services/origins'

// Estado
const origins = ref([])
const loading = ref(false)
const error = ref(null)
const saving = ref(false)

// Estado del modal
const showModal = ref(false)
const editingOrigin = ref(null)
const formData = ref({
  codigo: '',
  nombre: '',
  abreviacion: '',
  color: '#6B7280'
})
const formError = ref(null)

// Estado del diálogo de confirmación de eliminación
const showDeleteDialog = ref(false)
const originToDelete = ref(null)
const deleting = ref(false)

// Colores predefinidos
const presetColors = [
  '#DC2626', // rojo
  '#EA580C', // naranja
  '#CA8A04', // amarillo
  '#16A34A', // verde
  '#059669', // esmeralda
  '#0891B2', // cyan
  '#2563EB', // azul
  '#7C3AED', // violeta
  '#DB2777', // rosa
  '#6B7280', // gris
]

// Computed
const isEditing = computed(() => editingOrigin.value !== null)
const modalTitle = computed(() => isEditing.value ? 'Editar Origen' : 'Nuevo Origen')

// Cargar orígenes
async function fetchOrigins() {
  loading.value = true
  error.value = null

  try {
    const response = await originsService.getAll(true) // incluir inactivos
    origins.value = response.origins
  } catch (err) {
    error.value = err.userMessage || 'Error al cargar orígenes'
    console.error('Error fetching origins:', err)
  } finally {
    loading.value = false
  }
}

// Abrir modal para crear
function openCreateModal() {
  editingOrigin.value = null
  formData.value = {
    codigo: '',
    nombre: '',
    abreviacion: '',
    color: '#6B7280'
  }
  formError.value = null
  showModal.value = true
}

// Abrir modal para editar
function openEditModal(origin) {
  editingOrigin.value = origin
  formData.value = {
    codigo: origin.codigo,
    nombre: origin.nombre,
    abreviacion: origin.abreviacion,
    color: origin.color
  }
  formError.value = null
  showModal.value = true
}

// Guardar origen (crear o actualizar)
async function saveOrigin() {
  formError.value = null

  // Validación básica
  if (!formData.value.codigo.trim()) {
    formError.value = 'El código es requerido'
    return
  }
  if (!formData.value.nombre.trim()) {
    formError.value = 'El nombre es requerido'
    return
  }
  if (!formData.value.abreviacion.trim()) {
    formError.value = 'La abreviación es requerida'
    return
  }

  saving.value = true

  try {
    if (isEditing.value) {
      await originsService.update(editingOrigin.value.id, formData.value)
    } else {
      await originsService.create(formData.value)
    }

    showModal.value = false
    await fetchOrigins()
  } catch (err) {
    formError.value = err.userMessage || 'Error al guardar'
    console.error('Error saving origin:', err)
  } finally {
    saving.value = false
  }
}

// Confirmar eliminación
function confirmDelete(origin) {
  originToDelete.value = origin
  showDeleteDialog.value = true
}

// Eliminar origen
async function deleteOrigin() {
  if (!originToDelete.value) return

  deleting.value = true

  try {
    await originsService.delete(originToDelete.value.id)
    showDeleteDialog.value = false
    originToDelete.value = null
    await fetchOrigins()
  } catch (err) {
    error.value = err.userMessage || 'Error al eliminar'
    console.error('Error deleting origin:', err)
  } finally {
    deleting.value = false
  }
}

// Toggle activo/inactivo
async function toggleActive(origin) {
  try {
    await originsService.update(origin.id, { activo: !origin.activo })
    await fetchOrigins()
  } catch (err) {
    error.value = err.userMessage || 'Error al actualizar'
    console.error('Error toggling active:', err)
  }
}

onMounted(() => {
  fetchOrigins()
})
</script>

<template>
  <div class="h-full flex flex-col p-4 sm:p-6 overflow-auto">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-lg font-semibold text-zinc-800">Orígenes</h1>
        <p class="text-sm text-zinc-500 mt-1">
          Administra las categorías de origen de los documentos
        </p>
      </div>
      <Button @click="openCreateModal">
        <Plus class="w-4 h-4 mr-2" />
        Nuevo Origen
      </Button>
    </div>

    <!-- Mensaje de error -->
    <Transition name="slide-down">
      <div
        v-if="error"
        class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between"
      >
        <div class="flex items-center gap-2">
          <AlertCircle class="w-4 h-4 text-red-500 shrink-0" />
          <span class="text-red-700 text-sm">{{ error }}</span>
        </div>
        <button @click="error = null" class="text-red-400 hover:text-red-600">
          <X class="w-4 h-4" />
        </button>
      </div>
    </Transition>

    <!-- Estado de carga -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <div class="flex flex-col items-center">
        <Loader2 class="w-10 h-10 text-zinc-400 animate-spin mb-4" />
        <p class="text-zinc-500">Cargando orígenes...</p>
      </div>
    </div>

    <!-- Lista de orígenes -->
    <div v-else class="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
      <Card
        v-for="origin in origins"
        :key="origin.id"
        class="transition-all duration-200 hover:shadow-md"
        :class="{ 'opacity-50': !origin.activo }"
      >
        <CardHeader class="pb-2">
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-3">
              <div
                class="w-10 h-10 rounded-lg flex items-center justify-center"
                :style="{ backgroundColor: origin.color + '20' }"
              >
                <Tag class="w-5 h-5" :style="{ color: origin.color }" />
              </div>
              <div>
                <CardTitle class="text-base">{{ origin.abreviacion }}</CardTitle>
                <p class="text-xs text-zinc-500 font-mono">{{ origin.codigo }}</p>
              </div>
            </div>
            <div
              class="w-4 h-4 rounded-full border-2 border-white shadow"
              :style="{ backgroundColor: origin.color }"
            />
          </div>
        </CardHeader>
        <CardContent>
          <p class="text-sm text-zinc-600 mb-4">{{ origin.nombre }}</p>

          <div class="flex items-center justify-between">
            <!-- Badge de estado -->
            <span
              v-if="!origin.activo"
              class="text-xs px-2 py-1 rounded-full bg-zinc-200 text-zinc-600"
            >
              Inactivo
            </span>
            <span v-else class="text-xs px-2 py-1 rounded-full bg-green-100 text-green-700">
              Activo
            </span>

            <!-- Acciones -->
            <div class="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                class="w-8 h-8 text-zinc-400 hover:text-zinc-700"
                @click="openEditModal(origin)"
                title="Editar"
              >
                <Pencil class="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                class="w-8 h-8"
                :class="origin.activo ? 'text-zinc-400 hover:text-amber-500' : 'text-zinc-400 hover:text-green-500'"
                @click="toggleActive(origin)"
                :title="origin.activo ? 'Desactivar' : 'Activar'"
              >
                <Check v-if="!origin.activo" class="w-4 h-4" />
                <X v-else class="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                class="w-8 h-8 text-zinc-400 hover:text-red-500"
                @click="confirmDelete(origin)"
                title="Eliminar"
              >
                <Trash2 class="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Card vacía para agregar -->
      <Card
        v-if="origins.length === 0 && !loading"
        class="border-dashed border-2 flex items-center justify-center min-h-[200px] cursor-pointer hover:border-zinc-400 hover:bg-zinc-50 transition-colors"
        @click="openCreateModal"
      >
        <div class="text-center">
          <Plus class="w-10 h-10 text-zinc-400 mx-auto mb-2" />
          <p class="text-sm text-zinc-500">Crear primer origen</p>
        </div>
      </Card>
    </div>

    <!-- Modal de Crear/Editar -->
    <Dialog v-model:open="showModal">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{{ modalTitle }}</DialogTitle>
          <DialogDescription>
            {{ isEditing ? 'Modifica los datos del origen' : 'Completa los datos para crear un nuevo origen' }}
          </DialogDescription>
        </DialogHeader>

        <div class="space-y-4 py-4">
          <!-- Error del formulario -->
          <div v-if="formError" class="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p class="text-sm text-red-600">{{ formError }}</p>
          </div>

          <!-- Código -->
          <div class="space-y-2">
            <label class="text-sm font-medium text-zinc-700">Código</label>
            <Input
              v-model="formData.codigo"
              placeholder="ej: csjn_civ"
              class="font-mono"
              :disabled="saving"
            />
            <p class="text-xs text-zinc-500">Identificador único, sin espacios</p>
          </div>

          <!-- Nombre -->
          <div class="space-y-2">
            <label class="text-sm font-medium text-zinc-700">Nombre completo</label>
            <Input
              v-model="formData.nombre"
              placeholder="ej: Sentencias corte suprema de justicia - CIVIL"
              :disabled="saving"
            />
          </div>

          <!-- Abreviación -->
          <div class="space-y-2">
            <label class="text-sm font-medium text-zinc-700">Abreviación</label>
            <Input
              v-model="formData.abreviacion"
              placeholder="ej: CSJN Civil"
              :disabled="saving"
            />
            <p class="text-xs text-zinc-500">Texto corto para mostrar en la UI</p>
          </div>

          <!-- Color -->
          <div class="space-y-2">
            <label class="text-sm font-medium text-zinc-700">Color</label>
            <div class="flex items-center gap-3">
              <div class="flex gap-2 flex-wrap">
                <button
                  v-for="color in presetColors"
                  :key="color"
                  type="button"
                  class="w-8 h-8 rounded-lg border-2 transition-transform hover:scale-110"
                  :class="formData.color === color ? 'border-zinc-800 scale-110' : 'border-transparent'"
                  :style="{ backgroundColor: color }"
                  @click="formData.color = color"
                  :disabled="saving"
                />
              </div>
              <Input
                v-model="formData.color"
                type="color"
                class="w-12 h-8 p-0 border-0 cursor-pointer"
                :disabled="saving"
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" @click="showModal = false" :disabled="saving">
            Cancelar
          </Button>
          <Button @click="saveOrigin" :disabled="saving">
            <Loader2 v-if="saving" class="w-4 h-4 mr-2 animate-spin" />
            {{ isEditing ? 'Guardar cambios' : 'Crear origen' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Diálogo de confirmación de eliminación -->
    <Dialog v-model:open="showDeleteDialog">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle class="text-red-600">Eliminar Origen</DialogTitle>
          <DialogDescription>
            <p>¿Estás seguro de eliminar el origen <strong>{{ originToDelete?.nombre }}</strong>?</p>
            <p class="mt-2 text-sm text-amber-600">
              Solo se puede eliminar si no tiene documentos asociados.
            </p>
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" @click="showDeleteDialog = false" :disabled="deleting">
            Cancelar
          </Button>
          <Button variant="destructive" @click="deleteOrigin" :disabled="deleting">
            <Loader2 v-if="deleting" class="w-4 h-4 mr-2 animate-spin" />
            Eliminar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<style scoped>
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}
.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
