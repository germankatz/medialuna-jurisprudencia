<script setup>
import { computed } from 'vue'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { FileText, Download, ExternalLink, X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  file: { type: Object, default: null }
})

const emit = defineEmits(['update:open', 'download', 'open-external'])

const isOpen = computed({
  get: () => props.open,
  set: (value) => emit('update:open', value)
})

const handleDownload = () => {
  if (props.file) {
    emit('download', props.file)
  }
}

const handleOpenExternal = () => {
  if (props.file) {
    emit('open-external', props.file)
  }
}
</script>

<template>
  <Dialog v-model:open="isOpen">
    <DialogContent 
      class="max-w-4xl w-[95vw] h-[90vh] flex flex-col p-0 gap-0"
      :hide-close-button="true"
    >
      <!-- Header -->
      <DialogHeader class="px-4 sm:px-6 py-4 border-b shrink-0">
        <div class="flex items-start justify-between gap-4">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-10 h-10 rounded-lg bg-red-50 flex items-center justify-center shrink-0">
              <FileText class="w-5 h-5 text-red-500" />
            </div>
            <div class="min-w-0">
              <DialogTitle class="truncate">
                {{ file?.name || 'Documento' }}
              </DialogTitle>
              <DialogDescription v-if="file?.relevance" class="mt-1">
                Relevancia: {{ file.relevance }}%
                <span v-if="file?.page"> · Página {{ file.page }}</span>
              </DialogDescription>
            </div>
          </div>
          
          <!-- Acciones -->
          <div class="flex items-center gap-2 shrink-0">
            <Button 
              variant="outline" 
              size="icon"
              class="hidden sm:flex"
              @click="handleDownload"
            >
              <Download class="w-4 h-4" />
              <span class="sr-only">Descargar</span>
            </Button>
            <Button 
              variant="outline" 
              size="icon"
              class="hidden sm:flex"
              @click="handleOpenExternal"
            >
              <ExternalLink class="w-4 h-4" />
              <span class="sr-only">Abrir en nueva pestaña</span>
            </Button>
            <Button 
              variant="ghost" 
              size="icon"
              @click="isOpen = false"
            >
              <X class="w-4 h-4" />
              <span class="sr-only">Cerrar</span>
            </Button>
          </div>
        </div>
      </DialogHeader>

      <!-- Contenido del documento -->
      <div class="flex-1 overflow-hidden">
        <!-- Visor de PDF cuando hay previewUrl -->
        <template v-if="file?.previewUrl">
          <iframe
            :src="file.previewUrl"
            class="w-full h-full border-0"
            title="Vista previa del documento"
          />
        </template>
        
        <!-- Mostrar texto del fragmento si no hay previewUrl pero hay text -->
        <template v-else-if="file?.text">
          <ScrollArea class="h-full">
            <div class="p-4 sm:p-6">
              <div class="bg-white rounded-lg shadow-sm p-6 max-w-3xl mx-auto">
                <h4 class="text-sm font-medium text-zinc-500 mb-3">
                  Fragmento relevante:
                </h4>
                <p class="text-sm text-zinc-700 whitespace-pre-wrap leading-relaxed">
                  {{ file.text }}
                </p>
              </div>
            </div>
          </ScrollArea>
        </template>
        
        <!-- Placeholder cuando no hay contenido disponible -->
        <template v-else>
          <div class="h-full flex flex-col items-center justify-center text-center p-8">
            <FileText class="w-16 h-16 text-zinc-300 mb-4" />
            <h3 class="text-lg font-medium text-zinc-600 mb-2">
              Vista previa no disponible
            </h3>
            <p class="text-sm text-zinc-500 max-w-md">
              {{ file?.name || 'documento.pdf' }}
            </p>
          </div>
        </template>
      </div>

      <!-- Footer móvil con acciones -->
      <div class="sm:hidden border-t p-4 flex gap-2">
        <Button 
          variant="outline" 
          class="flex-1"
          @click="handleDownload"
        >
          <Download class="w-4 h-4 mr-2" />
          Descargar
        </Button>
        <Button 
          variant="outline" 
          class="flex-1"
          @click="handleOpenExternal"
        >
          <ExternalLink class="w-4 h-4 mr-2" />
          Abrir
        </Button>
      </div>
    </DialogContent>
  </Dialog>
</template>
