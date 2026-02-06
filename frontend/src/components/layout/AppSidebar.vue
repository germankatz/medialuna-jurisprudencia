<script setup>
import { ref } from 'vue'
import { Folder, Sparkles, Search, Croissant, Trash2, Tags, ClipboardCheck } from 'lucide-vue-next'
import SidebarButton from './SidebarButton.vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import api from '@/services/api'

defineProps({
  activeView: { type: String, required: true }
})

const emit = defineEmits(['update:activeView'])

const navItems = [
  { id: 'search', icon: Search, label: 'Buscar' },
  { id: 'documents', icon: Folder, label: 'Biblioteca' },
  { id: 'origins', icon: Tags, label: 'Orígenes' },
  { id: 'classify', icon: ClipboardCheck, label: 'Clasificar' },
  { id: 'chat', icon: Sparkles, label: 'Asistente', isAiIcon: true }
]

const handleNavClick = (viewId) => {
  emit('update:activeView', viewId)
}

const isBouncing = ref(false)

const handleLogoClick = () => {
  isBouncing.value = true
  setTimeout(() => {
    isBouncing.value = false
  }, 500)
}

const showResetDialog = ref(false)
const isResetting = ref(false)

const handleResetClick = () => {
  showResetDialog.value = true
}

const confirmReset = async () => {
  isResetting.value = true

  try {
    const response = await api.post('/documents/reset-all')
    console.log('Sistema reiniciado:', response.data)

    // Recargar la página para reflejar los cambios
    window.location.reload()

  } catch (error) {
    console.error('Error al reiniciar:', error)
    const errorMessage = error.userMessage || 'Error al reiniciar el sistema. Por favor, intenta nuevamente.'
    alert(errorMessage)
    isResetting.value = false
    showResetDialog.value = false
  }
}
</script>

<template>
  <aside 
    class="
      w-full md:w-20 lg:w-56
      h-16 md:h-screen 
      bg-zinc-900 
      flex md:flex-col 
      items-center lg:items-stretch
      justify-center md:justify-start 
      gap-2 md:gap-4 
      px-4 md:px-0 lg:px-4
      md:py-6
      order-last md:order-first
      border-t md:border-t-0 md:border-r
      border-zinc-800
      shrink-0
    "
  >
    <!-- Logo area (desktop) -->
    <div 
      class="hidden md:flex items-center lg:justify-start justify-center w-full mb-4 lg:px-2 cursor-pointer group"
      @click="handleLogoClick"
    >
      <div class="w-10 h-10 rounded-lg text-[#d3a779] flex items-center justify-center shrink-0">
        <Croissant 
          class="w-6 h-6 transition-transform duration-300 group-hover:rotate-45"
          :class="{ 'animate-bounce-croissant': isBouncing }"
        />
      </div>
      <span class="hidden lg:block text-white font-semibold text-lg">Medialuna</span>
    </div>

    <!-- Navigation buttons -->
    <nav class="flex md:flex-col gap-2 items-center flex-1">
      <!-- Logo (mobile) -->
      <div
        class="md:hidden w-10 h-10 rounded-lg text-[#d3a779] flex items-center justify-center shrink-0 cursor-pointer"
        @click="handleLogoClick"
      >
        <Croissant
          class="w-6 h-6 transition-transform duration-300 hover:rotate-45"
          :class="{ 'animate-bounce-croissant': isBouncing }"
        />
      </div>
      <SidebarButton
        v-for="item in navItems"
        :key="item.id"
        :icon="item.icon"
        :label="item.label"
        :active="activeView === item.id"
        :is-ai-icon="item.isAiIcon"
        @click="handleNavClick(item.id)"
      />
    </nav>

    <!-- Reset button (bottom) -->
    <div class="hidden md:block mt-auto px-2 lg:px-0">
      <Button
        variant="ghost"
        class="w-12 h-12 lg:w-full lg:h-10 flex items-center justify-center lg:justify-start lg:gap-3 lg:px-4 rounded-xl text-zinc-500 hover:text-red-400 hover:bg-zinc-800 transition-all duration-200 group"
        @click="handleResetClick"
      >
        <Trash2 class="w-5 h-5 shrink-0 group-hover:text-red-400" />
        <span class="sr-only lg:not-sr-only lg:text-sm lg:font-medium">Reiniciar</span>
      </Button>
    </div>

    <!-- Confirmation Dialog -->
    <Dialog v-model:open="showResetDialog">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle class="text-red-600">Confirmar Reinicio</DialogTitle>
          <DialogDescription class="space-y-2">
            <p class="font-semibold">Esta acción eliminará TODA la información del sistema:</p>
            <ul class="list-disc list-inside space-y-1 text-sm">
              <li>Todos los documentos de la base de datos</li>
              <li>Toda la memoria vectorial (ChromaDB)</li>
              <li>Todos los archivos PDF almacenados</li>
            </ul>
            <p class="font-bold text-red-600 mt-3">Esta acción no se puede deshacer.</p>
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="gap-2 sm:gap-0">
          <Button
            variant="outline"
            @click="showResetDialog = false"
            :disabled="isResetting"
          >
            Cancelar
          </Button>
          <Button
            variant="destructive"
            @click="confirmReset"
            :disabled="isResetting"
          >
            {{ isResetting ? 'Reiniciando...' : 'Confirmar Reinicio' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </aside>
</template>

<style scoped>
@keyframes bounce-croissant {
  0%, 100% {
    transform: translateY(0) rotate(45deg);
  }
  25% {
    transform: translateY(-8px) rotate(35deg);
  }
  50% {
    transform: translateY(0) rotate(55deg);
  }
  75% {
    transform: translateY(-4px) rotate(40deg);
  }
}

.animate-bounce-croissant {
  animation: bounce-croissant 0.5s ease-in-out;
  transform: rotate(45deg);
}
</style>
