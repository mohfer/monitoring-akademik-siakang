<template>
    <div @click.self="$emit('close')"
        class="fixed inset-0 bg-black/60 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
        <div class="bg-background border-t sm:border border-border rounded-t-lg sm:rounded-lg w-full sm:max-w-lg h-[90vh] sm:h-auto sm:max-h-[90vh] flex flex-col overflow-hidden">
            <!-- Header -->
            <div class="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
                <h2 class="text-sm font-semibold flex items-center gap-2">
                    <Edit3 v-if="task" :size="16" class="text-muted-foreground" />
                    <Plus v-else :size="16" class="text-muted-foreground" />
                    {{ task ? 'Edit Task' : 'New Task' }}
                </h2>
                <Button variant="ghost" size="icon" class="h-8 w-8" @click="$emit('close')">
                    <X :size="14" />
                </Button>
            </div>

            <!-- Form -->
            <div class="flex-1 overflow-y-auto p-5 space-y-4 custom-scrollbar">
                <!-- Name -->
                <div>
                    <label class="block text-xs font-medium text-muted-foreground mb-1.5">Name</label>
                    <Input v-model="form.name" required placeholder="Task name" />
                </div>

                <!-- Monitor Type -->
                <div>
                    <label class="block text-xs font-medium text-muted-foreground mb-1.5">Type</label>
                    <div class="flex gap-2">
                        <Button type="button" @click="form.monitor_type = 'nilai'"
                            :variant="form.monitor_type === 'nilai' ? 'default' : 'outline'"
                            class="flex-1">
                            Nilai
                        </Button>
                        <Button type="button" @click="form.monitor_type = 'krs'"
                            :variant="form.monitor_type === 'krs' ? 'default' : 'outline'"
                            class="flex-1">
                            KRS
                        </Button>
                    </div>
                </div>

                <!-- Login -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-medium text-muted-foreground mb-1.5">Login ID</label>
                        <Input v-model="form.login_id" required placeholder="NIM/Email" />
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-muted-foreground mb-1.5">Password</label>
                        <div class="relative">
                            <Input v-model="form.password" :type="showPassword ? 'text' : 'password'" required
                                class="pr-9" placeholder="••••••" />
                            <Button type="button" variant="ghost" size="icon"
                                @click="showPassword = !showPassword"
                                class="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8">
                                <Eye v-if="!showPassword" :size="14" />
                                <EyeOff v-else :size="14" />
                            </Button>
                        </div>
                    </div>
                </div>

                <!-- Notifications -->
                <div class="pt-2">
                    <label class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground mb-3 pb-2 border-b border-border">
                        <Bell :size="14" />
                        Notifications
                    </label>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label class="block text-xs text-muted-foreground mb-1.5">Telegram Chat ID</label>
                            <Input v-model="form.chat_id" placeholder="123456789" />
                            <a href="https://t.me/userinfobot" target="_blank"
                                class="text-xs text-muted-foreground hover:text-foreground mt-1 inline-flex items-center gap-0.5">
                                Find ID <ExternalLink :size="10" />
                            </a>
                        </div>
                        <div>
                            <label class="block text-xs text-muted-foreground mb-1.5">WhatsApp Number</label>
                            <Input v-model="form.whatsapp_number" placeholder="628..." />
                            <p class="text-xs text-muted-foreground mt-1">628... or Group ID</p>
                        </div>
                    </div>
                    <div v-if="form.monitor_type === 'nilai'" class="mt-3 pt-3 border-t border-border">
                        <p class="text-xs font-medium text-muted-foreground mb-2">Notification mode per channel</p>
                        <div class="space-y-2 ml-1">
                            <label v-if="form.chat_id" class="flex items-center gap-2.5 cursor-pointer select-none group">
                                <div class="relative" @click="form.notify_without_grades_telegram = !form.notify_without_grades_telegram">
                                    <div class="h-5 w-9 rounded-full transition-colors" :class="form.notify_without_grades_telegram ? 'bg-primary' : 'bg-input'"></div>
                                    <div class="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-background shadow-sm transition-transform" :class="form.notify_without_grades_telegram ? 'translate-x-4' : ''"></div>
                                </div>
                                <span class="text-xs text-muted-foreground group-hover:text-foreground transition-colors">Telegram: notification only (no grade values)</span>
                            </label>
                            <label v-if="form.whatsapp_number" class="flex items-center gap-2.5 cursor-pointer select-none group">
                                <div class="relative" @click="form.notify_without_grades_whatsapp = !form.notify_without_grades_whatsapp">
                                    <div class="h-5 w-9 rounded-full transition-colors" :class="form.notify_without_grades_whatsapp ? 'bg-primary' : 'bg-input'"></div>
                                    <div class="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-background shadow-sm transition-transform" :class="form.notify_without_grades_whatsapp ? 'translate-x-4' : ''"></div>
                                </div>
                                <span class="text-xs text-muted-foreground group-hover:text-foreground transition-colors">WhatsApp: notification only (no grade values)</span>
                            </label>
                        </div>
                        <p class="text-[11px] text-muted-foreground/50 mt-2 ml-1">Toggle on to receive only a "grades are out" alert without the actual scores.</p>
                    </div>
                    <div v-if="!form.chat_id && !form.whatsapp_number"
                        class="mt-2 flex items-start gap-1.5 text-xs text-destructive">
                        <AlertCircle :size="12" class="mt-0.5 shrink-0" />
                        <span>At least one notification channel required.</span>
                    </div>
                </div>

                <!-- Target Courses (KRS only) -->
                <div v-if="form.monitor_type === 'krs'">
                    <label class="block text-xs font-medium text-muted-foreground mb-1.5">
                        Target Courses <span class="text-muted-foreground/50">(one per line)</span>
                    </label>
                    <textarea v-model="form.target_courses_text" rows="3"
                        class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                        placeholder="Pemrograman Berorientasi Objek&#10;Data Mining"></textarea>
                </div>

                <!-- Semester & Interval -->
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="flex items-center justify-between text-xs font-medium text-muted-foreground mb-1.5">
                            Semester
                            <button type="button" @click="fetchSemesters" :disabled="isLoadingSemesters"
                                class="text-muted-foreground hover:text-foreground flex items-center gap-0.5">
                                <span v-if="isLoadingSemesters">...</span>
                                <span v-else class="flex items-center gap-0.5"><RefreshCw :size="10" /> Fetch</span>
                            </button>
                        </label>
                        <div v-if="semestersList.length > 0" class="relative">
                            <select v-model="form.target_semester_code"
                                class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 appearance-none cursor-pointer pr-7">
                                <option value="">Auto</option>
                                <option v-for="sem in semestersList" :key="sem.code" :value="sem.code">{{ sem.title }}</option>
                            </select>
                            <ChevronDown :size="12" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                        </div>
                        <Input v-else v-model="form.target_semester_code" placeholder="Optional" />
                        <p v-if="fetchError" class="text-xs text-destructive mt-1">{{ fetchError }}</p>
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-muted-foreground mb-1.5">Interval (sec)</label>
                        <Input v-model.number="form.interval" type="number" min="60" />
                    </div>
                </div>
            </div>

            <!-- Actions -->
            <div class="flex items-center justify-end gap-2 px-5 py-4 border-t border-border shrink-0">
                <Button variant="ghost" @click="$emit('close')">
                    Cancel
                </Button>
                <Button @click="save">
                    {{ task ? 'Save' : 'Create' }}
                </Button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import axios from 'axios'
import Button from './ui/Button.vue'
import Input from './ui/Input.vue'
import { X, Edit3, Plus, Eye, EyeOff, RefreshCw, ChevronDown, Bell, AlertCircle, ExternalLink } from 'lucide-vue-next'

const props = defineProps(['task'])
const emit = defineEmits(['close', 'save'])

const showPassword = ref(false)
const isLoadingSemesters = ref(false)
const semestersList = ref([])
const fetchError = ref('')

const form = ref({
    name: '',
    login_id: '',
    password: '',
    chat_id: '',
    whatsapp_number: '',
    target_semester_code: '',
    interval: 300,
    monitor_type: 'nilai',
    target_courses_text: '',
    notify_without_grades_telegram: false,
    notify_without_grades_whatsapp: false
})

watch(() => props.task, (newVal) => {
    semestersList.value = []
    fetchError.value = ''
    if (newVal) {
        let tcText = ''
        if (newVal.target_courses) {
            try {
                const arr = JSON.parse(newVal.target_courses)
                tcText = Array.isArray(arr) ? arr.join('\n') : newVal.target_courses
            } catch {
                tcText = newVal.target_courses
            }
        }
        form.value = {
            ...newVal,
            monitor_type: newVal.monitor_type || 'nilai',
            whatsapp_number: newVal.whatsapp_number || '',
            target_courses_text: tcText,
            notify_without_grades_telegram: Boolean(newVal.notify_without_grades_telegram),
            notify_without_grades_whatsapp: Boolean(newVal.notify_without_grades_whatsapp)
        }
    } else {
        form.value = {
            name: '',
            login_id: '',
            password: '',
            chat_id: '',
            whatsapp_number: '',
            target_semester_code: '',
            interval: 300,
            monitor_type: 'nilai',
            target_courses_text: '',
            notify_without_grades_telegram: false,
            notify_without_grades_whatsapp: false
        }
    }
}, { immediate: true })

const fetchSemesters = async () => {
    if (!form.value.login_id || !form.value.password) {
        fetchError.value = "Enter Login ID and Password first."
        return
    }
    isLoadingSemesters.value = true
    fetchError.value = ''
    semestersList.value = []
    try {
        const res = await axios.post('/api/check-semesters', {
            login_id: form.value.login_id,
            password: form.value.password
        })
        semestersList.value = res.data.semesters
        if (semestersList.value.length === 0) {
            fetchError.value = "No semesters found."
        }
    } catch (e) {
        fetchError.value = e.response?.data?.detail || "Failed to fetch"
    } finally {
        isLoadingSemesters.value = false
    }
}

const save = () => {
    const payload = { ...form.value }
    if (!payload.chat_id && !payload.whatsapp_number) {
        alert("Provide at least one notification channel.")
        return
    }
    const lines = payload.target_courses_text
        ? payload.target_courses_text.split('\n').map(l => l.trim()).filter(l => l)
        : []
    payload.target_courses = JSON.stringify(lines)
    delete payload.target_courses_text
    emit('save', payload)
}
</script>
