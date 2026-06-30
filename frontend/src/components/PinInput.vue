<script setup>
import { ref, nextTick } from 'vue'
import axios from 'axios'
import Button from './ui/Button.vue'
import { Lock, AlertCircle } from 'lucide-vue-next'

const emit = defineEmits(['authenticated'])

const pin = ref(['', '', '', ''])
const inputRefs = ref([])
const loading = ref(false)
const error = ref('')
const shake = ref(false)

const API_URL = '/api'

const handleInput = (index) => {
    const value = pin.value[index]
    if (value.length > 1) {
        pin.value[index] = value.slice(-1)
    }
    if (value && index < 3) {
        inputRefs.value[index + 1]?.focus()
    }
    error.value = ''
    checkComplete()
}

const handleKeydown = (index, e) => {
    if (e.key === 'Backspace' && !pin.value[index] && index > 0) {
        inputRefs.value[index - 1]?.focus()
    }
}

const handlePaste = (e) => {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 4)
    for (let i = 0; i < pasted.length; i++) {
        pin.value[i] = pasted[i]
    }
    if (pasted.length > 0) {
        const focusIndex = Math.min(pasted.length, 3)
        inputRefs.value[focusIndex]?.focus()
    }
    checkComplete()
}

const checkComplete = () => {
    if (pin.value.every(d => d !== '')) {
        verifyPin()
    }
}

const verifyPin = async () => {
    loading.value = true
    error.value = ''
    const pinString = pin.value.join('')
    
    try {
        await axios.post(`${API_URL}/verify-pin`, { pin: pinString })
        localStorage.setItem('siakang_pin_verified', 'true')
        emit('authenticated')
    } catch (e) {
        error.value = 'PIN salah, coba lagi'
        shake.value = true
        setTimeout(() => {
            shake.value = false
            pin.value = ['', '', '', '']
            inputRefs.value[0]?.focus()
        }, 500)
    } finally {
        loading.value = false
    }
}
</script>

<template>
    <div class="h-screen flex items-center justify-center bg-background p-4">
        <div :class="['w-full max-w-xs text-center', shake && 'animate-shake']">
            <div class="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-6">
                <Lock :size="28" class="text-primary" />
            </div>
            
            <h1 class="text-lg font-semibold mb-1">Masukkan PIN</h1>
            <p class="text-sm text-muted-foreground mb-8">4 digit untuk masuk ke aplikasi</p>
            
            <div class="flex justify-center gap-3 mb-6">
                <input
                    v-for="(_, i) in 4"
                    :key="i"
                    :ref="el => inputRefs[i] = el"
                    v-model="pin[i]"
                    type="password"
                    inputmode="numeric"
                    maxlength="1"
                    :disabled="loading"
                    class="w-14 h-14 text-center text-xl font-semibold rounded-lg border border-input bg-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 transition-all"
                    @input="handleInput(i)"
                    @keydown="handleKeydown(i, $event)"
                    @paste="handlePaste"
                />
            </div>
            
            <p v-if="error" class="flex items-center justify-center gap-1.5 text-sm text-destructive mb-4">
                <AlertCircle :size="14" />
                {{ error }}
            </p>
            
            <Button @click="verifyPin" :disabled="loading || pin.some(d => !d)" class="w-full">
                {{ loading ? 'Memverifikasi...' : 'Masuk' }}
            </Button>
        </div>
    </div>
</template>

<style scoped>
@keyframes shake {
    0%, 100% { transform: translateX(0); }
    20%, 60% { transform: translateX(-8px); }
    40%, 80% { transform: translateX(8px); }
}
.animate-shake {
    animation: shake 0.5s ease-in-out;
}
</style>
