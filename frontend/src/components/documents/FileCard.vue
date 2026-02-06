<script setup>
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, Trash2 } from 'lucide-vue-next'

defineProps({
  file: { 
    type: Object, 
    required: true,
    validator: (value) => 'id' in value && 'name' in value
  }
})

const emit = defineEmits(['click', 'delete'])

const handleClick = () => {
  emit('click')
}

const handleDelete = (event) => {
  event.stopPropagation()
  emit('delete')
}
</script>

<template>
  <Card 
    class="
      relative group 
      hover:shadow-md 
      transition-all duration-200 
      cursor-pointer
      bg-white
    "
    @click="handleClick"
  >
    <CardContent class="flex flex-col items-center p-4 sm:p-6">
      <FileText class="w-10 h-10 sm:w-12 sm:h-12 text-zinc-400 mb-2" />
      <p 
        class="
          text-xs sm:text-sm 
          text-zinc-700 
          truncate 
          w-full 
          text-center
          font-medium
        "
        :title="file.caratula || file.name"
      >
        {{ file.caratula || file.name }}
      </p>
      <div class="mt-2 flex items-center justify-center w-full">
        <span
          v-if="file.origen"
          class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium"
          :style="{
            backgroundColor: file.origen.color + '15',
            color: file.origen.color
          }"
        >
          <span
            class="w-1.5 h-1.5 rounded-full"
            :style="{ backgroundColor: file.origen.color }"
          />
          {{ file.origen.abreviacion }}
        </span>
        <span v-else class="text-[11px] text-zinc-400">
          Sin origen
        </span>
      </div>
    </CardContent>
    
    <!-- Botón de eliminar -->
    <Button
      variant="ghost"
      size="icon"
      class="
        absolute top-2 right-2 
        w-8 h-8
        text-zinc-400 hover:text-red-500 hover:bg-red-50
        opacity-100 md:opacity-0 md:group-hover:opacity-100
        transition-opacity duration-200
      "
      @click="handleDelete"
    >
      <Trash2 class="w-4 h-4" />
      <span class="sr-only">Eliminar archivo</span>
    </Button>
  </Card>
</template>
