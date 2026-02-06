<script setup>
import { Card } from '@/components/ui/card'
import { FileText, ExternalLink } from 'lucide-vue-next'

defineProps({
  file: {
    type: Object,
    required: true,
    validator: (value) => 'id' in value && 'name' in value
  }
})

const emit = defineEmits(['click'])

const handleClick = () => {
  emit('click')
}
</script>

<template>
  <Card 
    class="
      flex items-center gap-3 
      p-3 
      bg-white/80 
      hover:bg-white 
      cursor-pointer 
      transition-colors 
      border border-zinc-200
      group
    "
    @click="handleClick"
  >
    <div class="w-10 h-10 rounded-lg bg-red-50 flex items-center justify-center shrink-0">
      <FileText class="w-5 h-5 text-red-500" />
    </div>
    
    <div class="flex-1 min-w-0">
      <p class="text-sm font-medium text-zinc-800 truncate" :title="file.name">
        {{ file.name }}
      </p>
      <div class="flex items-center gap-2 mt-0.5">
        <!-- Badge de origen -->
        <span
          v-if="file.origen"
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium"
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
        <p v-if="file.relevance" class="text-xs text-zinc-500">
          {{ file.relevance }}%
        </p>
        <p v-else-if="file.page" class="text-xs text-zinc-500">
          Pág. {{ file.page }}
        </p>
      </div>
    </div>
    
    <ExternalLink 
      class="w-4 h-4 text-zinc-400 group-hover:text-zinc-600 transition-colors shrink-0" 
    />
  </Card>
</template>
