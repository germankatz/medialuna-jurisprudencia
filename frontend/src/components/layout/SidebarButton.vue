<script setup>
import { computed } from 'vue'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const props = defineProps({
  icon: { type: Object, required: true },
  label: { type: String, required: true },
  active: { type: Boolean, default: false },
  isAiIcon: { type: Boolean, default: false }
})

defineEmits(['click'])

const buttonClasses = computed(() => 
  cn(
    'w-12 h-12 md:w-14 md:h-14 lg:w-full lg:h-12 flex items-center justify-center lg:justify-start lg:gap-3 lg:px-4 rounded-xl transition-all duration-200',
    props.active 
      ? 'bg-zinc-700 text-white hover:bg-zinc-600' 
      : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
  )
)

const iconClasses = computed(() => 
  cn(
    'w-6 h-6 md:w-7 md:h-7 lg:w-5 lg:h-5 shrink-0 transition-all duration-200',
    props.isAiIcon && 'group-hover:text-yellow-400 group-hover:drop-shadow-[0_0_6px_rgba(250,204,21,0.7)]'
  )
)
</script>

<template>
  <Button
    variant="ghost"
    :class="buttonClasses"
    class="group"
    @click="$emit('click')"
  >
    <component :is="icon" :class="iconClasses" />
    <span class="sr-only lg:not-sr-only lg:text-sm lg:font-medium">{{ label }}</span>
  </Button>
</template>
