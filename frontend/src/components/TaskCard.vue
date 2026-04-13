<template>
    <Card class="group p-3 sm:p-4 hover:border-muted-foreground/50 transition-colors flex flex-col">
        <!-- Header -->
        <div class="flex items-start justify-between mb-2 sm:mb-3">
            <div class="flex items-center gap-2 min-w-0">
                <Badge :variant="task.status === 'running' ? 'default' : 'secondary'" class="gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full" :class="task.status === 'running' ? 'bg-primary-foreground animate-pulse' : 'bg-muted-foreground'"></span>
                    {{ task.status }}
                </Badge>
                <span class="text-xs font-mono text-muted-foreground truncate">{{ task.login_id }}</span>
            </div>
            <div class="drag-handle cursor-grab active:cursor-grabbing p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-accent transition-all shrink-0">
                <GripVertical :size="14" class="text-muted-foreground" />
            </div>
        </div>

        <!-- Title -->
        <h3 class="text-sm font-semibold mb-2 sm:mb-3 truncate">{{ task.name }}</h3>

        <!-- Meta -->
        <div class="space-y-1.5 mb-3 sm:mb-4 flex-grow">
            <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">Type</span>
                <span class="font-mono uppercase">{{ task.monitor_type || 'nilai' }}</span>
            </div>
            <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">Semester</span>
                <span class="font-mono truncate ml-2">{{ task.target_semester_code || 'Auto' }}</span>
            </div>
            <div class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">Interval</span>
                <span class="font-mono">{{ task.interval }}s</span>
            </div>
            <div v-if="task.pid" class="flex items-center justify-between text-xs">
                <span class="text-muted-foreground">PID</span>
                <span class="font-mono">{{ task.pid }}</span>
            </div>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-1 pt-2 sm:pt-3 border-t border-border">
            <Button @click="toggleStatus" variant="ghost" size="sm"
                :class="[
                    'flex-1 gap-1.5',
                    task.status === 'running'
                        ? 'text-destructive hover:text-destructive hover:bg-destructive/10'
                        : 'text-green-600 dark:text-green-400 hover:text-green-600 dark:hover:text-green-400 hover:bg-green-50 dark:hover:bg-green-950'
                ]">
                <Square v-if="task.status === 'running'" :size="12" class="fill-current" />
                <Play v-else :size="12" class="fill-current" />
                {{ task.status === 'running' ? 'Stop' : 'Start' }}
            </Button>
            <div class="w-px h-5 bg-border hidden sm:block"></div>
            <Button variant="ghost" size="icon" class="h-8 w-8" @click="showLogs" title="Logs">
                <FileText :size="14" />
            </Button>
            <Button variant="ghost" size="icon" class="h-8 w-8" @click="showData" title="Data">
                <Table :size="14" />
            </Button>
            <Button variant="ghost" size="icon" class="h-8 w-8 hidden sm:flex" @click="$emit('clone')" title="Clone">
                <Copy :size="14" />
            </Button>
            <div class="w-px h-5 bg-border hidden sm:block"></div>
            <Button variant="ghost" size="icon" class="h-8 w-8" @click="$emit('edit')" title="Edit">
                <Edit :size="14" />
            </Button>
            <Button variant="ghost" size="icon" class="h-8 w-8 hover:text-destructive hover:bg-destructive/10" @click="$emit('delete')" title="Delete">
                <Trash2 :size="14" />
            </Button>
        </div>

        <!-- Logs Modal -->
        <div v-if="showingLogs" @click.self="closeLogs"
            class="fixed inset-0 bg-black/60 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
            <div class="bg-background border-t sm:border border-border rounded-t-lg sm:rounded-lg w-full sm:max-w-4xl h-[90vh] sm:h-[85vh] flex flex-col overflow-hidden">
                <div class="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
                    <div class="flex items-center gap-2 min-w-0">
                        <FileText :size="16" class="text-muted-foreground shrink-0" />
                        <h3 class="text-sm font-medium truncate">Logs: {{ task.name }}</h3>
                    </div>
                    <div class="flex items-center gap-1 shrink-0">
                        <Button variant="ghost" size="icon" class="h-8 w-8 hover:text-destructive hover:bg-destructive/10" @click="clearLogs">
                            <Trash2 :size="14" />
                        </Button>
                        <Button variant="ghost" size="icon" class="h-8 w-8" @click="closeLogs">
                            <X :size="14" />
                        </Button>
                    </div>
                </div>
                <div class="flex-1 overflow-auto bg-muted/50 custom-scrollbar">
                    <div v-if="logs === 'Loading...'" class="flex items-center justify-center h-full text-muted-foreground text-sm">
                        <Loader2 :size="16" class="animate-spin mr-2" /> Loading...
                    </div>
                    <pre v-else class="p-3 sm:p-4 text-xs font-mono whitespace-pre-wrap leading-relaxed" v-html="formattedLogs"></pre>
                </div>
                <div class="flex items-center justify-between px-4 py-2 border-t border-border text-xs text-muted-foreground shrink-0">
                    <div class="flex items-center gap-1.5">
                        <div class="w-1.5 h-1.5 rounded-full bg-green-500"></div>
                        <span>Live</span>
                    </div>
                    <span>Last 200 lines</span>
                </div>
            </div>
        </div>

        <!-- Data Modal -->
        <div v-if="showingData" @click.self="showingData = false"
            class="fixed inset-0 bg-black/60 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
            <div class="bg-background border-t sm:border border-border rounded-t-lg sm:rounded-lg w-full sm:max-w-4xl h-[90vh] sm:max-h-[85vh] flex flex-col overflow-hidden">
                <div class="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
                    <div class="flex items-center gap-2 min-w-0">
                        <Table :size="16" class="text-muted-foreground shrink-0" />
                        <h3 class="text-sm font-medium truncate">Data: {{ task.name }}</h3>
                    </div>
                    <div class="flex items-center gap-1 shrink-0">
                        <Button variant="ghost" size="icon" class="h-8 w-8 hover:text-destructive hover:bg-destructive/10" @click="clearData">
                            <Trash2 :size="14" />
                        </Button>
                        <Button variant="ghost" size="icon" class="h-8 w-8" @click="refreshData" :disabled="isRefreshing">
                            <RotateCw :size="14" :class="{ 'animate-spin': isRefreshing }" />
                        </Button>
                        <Button variant="ghost" size="icon" class="h-8 w-8" @click="showingData = false">
                            <X :size="14" />
                        </Button>
                    </div>
                </div>

                <div class="flex-1 overflow-auto p-3 sm:p-4 custom-scrollbar">
                    <div v-if="!hasDataDisplay" class="text-center text-muted-foreground py-12 text-sm">
                        <Table :size="32" class="mx-auto mb-3 text-muted-foreground/50" />
                        <p>No data yet.</p>
                    </div>
                    <div v-else class="flex flex-col gap-3 sm:gap-4">
                        <!-- User Info -->
                        <div v-if="resultData && resultData.nama" class="flex flex-col sm:flex-row sm:items-center justify-between p-3 bg-muted/50 rounded-lg border border-border gap-2">
                            <div>
                                <h4 class="text-sm font-medium">{{ resultData.nama }}</h4>
                                <p class="text-xs font-mono text-muted-foreground">{{ resultData.nim }}</p>
                            </div>
                            <div class="flex gap-4 text-center">
                                <div>
                                    <p class="text-xs text-muted-foreground uppercase">SKS</p>
                                    <p class="text-sm font-mono font-semibold">{{ resultData.total_sks ?? '-' }}</p>
                                </div>
                                <div>
                                    <p class="text-xs text-muted-foreground uppercase">Courses</p>
                                    <p class="text-sm font-mono font-semibold">{{ courseData.length }}</p>
                                </div>
                            </div>
                        </div>

                        <!-- GPA -->
                        <div v-if="gpaData.length > 0" class="grid grid-cols-2 gap-2 sm:gap-3">
                            <Card v-for="(item, idx) in gpaData" :key="idx" class="p-2 sm:p-3">
                                <p class="text-xs text-muted-foreground mb-1">{{ item.matkul }}</p>
                                <p class="text-xl sm:text-2xl font-mono font-bold">{{ item.nilai }}</p>
                            </Card>
                        </div>

                        <!-- KRS Status -->
                        <Card v-if="task.monitor_type === 'krs'" class="overflow-hidden">
                            <div class="px-4 py-2.5 border-b border-border bg-muted/50">
                                <h4 class="text-xs font-medium uppercase tracking-wider text-muted-foreground">Target Courses</h4>
                            </div>
                            <div v-if="krsCourseStatus.length > 0">
                                <div v-for="(item, idx) in krsCourseStatus" :key="idx"
                                    class="flex items-center gap-3 px-4 py-2.5 border-b border-border last:border-0">
                                    <div class="w-2 h-2 rounded-full shrink-0" :class="item.found ? 'bg-green-500' : 'bg-red-500'"></div>
                                    <span class="text-sm flex-1 min-w-0 truncate">{{ item.name }}</span>
                                    <Badge :variant="item.found ? 'default' : 'destructive'" class="text-xs">
                                        {{ item.found ? 'Found' : 'Missing' }}
                                    </Badge>
                                </div>
                            </div>
                            <div v-else class="px-4 py-6 text-center text-sm text-muted-foreground">No targets configured.</div>
                        </Card>

                        <!-- Grades Table -->
                        <Card v-else class="overflow-x-auto">
                            <table class="w-full text-sm min-w-[400px]">
                                <thead>
                                    <tr class="border-b border-border bg-muted/50">
                                        <th class="text-left px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Mata Kuliah</th>
                                        <th class="text-center px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">SKS</th>
                                        <th class="text-center px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Nilai</th>
                                        <th class="text-center px-4 py-2.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">Mutu</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="(item, idx) in courseData" :key="idx"
                                        class="border-b border-border last:border-0">
                                        <td class="px-4 py-2.5">{{ item.matkul }}</td>
                                        <td class="px-4 py-2.5 text-center font-mono text-muted-foreground">{{ item.sks || '-' }}</td>
                                        <td class="px-4 py-2.5 text-center">
                                            <span class="font-mono" :class="item.nilai !== '---' ? 'font-semibold' : 'text-muted-foreground'">
                                                {{ item.nilai }}
                                            </span>
                                        </td>
                                        <td class="px-4 py-2.5 text-center font-mono">{{ item.mutu !== '---' ? item.mutu : '-' }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </Card>
                    </div>
                </div>
            </div>
        </div>
    </Card>
</template>

<script setup>
import { computed, ref, onUnmounted, nextTick } from 'vue'
import axios from 'axios'
import Card from './ui/Card.vue'
import Badge from './ui/Badge.vue'
import Button from './ui/Button.vue'
import { Play, Square, FileText, Edit, Trash2, X, Loader2, Table, RotateCw, Copy, GripVertical } from 'lucide-vue-next'

const props = defineProps(['task'])
const emit = defineEmits(['edit', 'delete', 'refresh', 'clone'])

const showingLogs = ref(false)
const showingData = ref(false)
const isRefreshing = ref(false)
const logs = ref('Loading...')
const resultData = ref(null)
const logContainer = ref(null)
const API_URL = '/api'
let logInterval = null

const formattedLogs = computed(() => {
    if (!logs.value || logs.value === 'Loading...') return logs.value

    let text = logs.value
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')

    const colorMap = {
        '30': '#1a1a1a', '31': '#ef4444', '32': '#22c55e', '33': '#eab308',
        '34': '#3b82f6', '35': '#ec4899', '36': '#06b6d4', '37': '#d1d5db',
        '90': '#6b7280', '91': '#f87171', '92': '#4ade80', '93': '#facc15',
        '94': '#60a5fa', '95': '#f472b6', '96': '#22d3ee', '97': '#f3f4f6'
    }

    text = text.replace(/\x1b\[([0-9;]+)m/g, (match, codes) => {
        if (codes === '0') return '</span>'
        const codeList = codes.split(';')
        const styles = []
        for (const code of codeList) {
            if (colorMap[code]) styles.push(`color: ${colorMap[code]}`)
            if (code === '1') styles.push('font-weight: bold')
        }
        return styles.length > 0 ? `<span style="${styles.join('; ')}">` : ''
    })

    const tagColors = {
        '\\[ERROR\\]': 'color: #ef4444; font-weight: bold',
        '\\[SUCCESS\\]': 'color: #22c55e; font-weight: bold',
        '\\[WARNING\\]': 'color: #eab308; font-weight: bold',
        '\\[INFO\\]': 'color: #06b6d4; font-weight: bold',
        '\\[STATUS\\]': 'color: #3b82f6; font-weight: bold',
        '\\[ALERT\\]': 'color: #ec4899; font-weight: bold',
        '\\[COMPLETE\\]': 'color: #22c55e; font-weight: bold',
        '\\[UPDATE\\]': 'color: #06b6d4; font-weight: bold',
        '\\[GAGAL\\]': 'color: #ef4444; font-weight: bold',
        '\\[SUKSES\\]': 'color: #22c55e; font-weight: bold',
        '\\[PERINGATAN\\]': 'color: #eab308; font-weight: bold'
    }

    for (const [tag, style] of Object.entries(tagColors)) {
        const regex = new RegExp(`(?<!<span[^>]*>)${tag}(?![^<]*<\\/span>)`, 'g')
        text = text.replace(regex, (match) => {
            return `<span style="${style}">${match}</span>`
        })
    }

    const openCount = (text.match(/<span/g) || []).length
    const closeCount = (text.match(/<\/span>/g) || []).length
    if (openCount > closeCount) {
        text += '</span>'.repeat(openCount - closeCount)
    }

    return text
})

const courseData = computed(() => {
    if (!resultData.value || !resultData.value.nilai) return []
    return resultData.value.nilai.filter(item => !item.matkul.includes('Indeks Prestasi'))
})

const gpaData = computed(() => {
    if (!resultData.value) return []
    if (resultData.value.ips && resultData.value.ipk) {
        return [
            { matkul: "IP", nilai: resultData.value.ips },
            { matkul: "IPK", nilai: resultData.value.ipk }
        ]
    }
    if (Array.isArray(resultData.value)) {
        return resultData.value.filter(item => item.matkul.includes('Indeks Prestasi'))
    }
    return []
})

const krsCourseStatus = computed(() => {
    if (props.task.monitor_type !== 'krs') return []

    let targets = []
    try {
        if (props.task.target_courses) {
            targets = JSON.parse(props.task.target_courses)
            if (!Array.isArray(targets)) targets = []
        }
    } catch (e) {
        targets = []
    }

    const found = resultData.value && resultData.value.found ? resultData.value.found : []

    return targets.map(course => ({
        name: course,
        found: found.includes(course)
    }))
})

const hasDataDisplay = computed(() => {
    if (props.task.monitor_type === 'krs') {
        const t = props.task.target_courses
        return t && t !== '[]' && t !== 'null'
    }
    return resultData.value && (resultData.value.nilai || (Array.isArray(resultData.value) && resultData.value.length > 0))
})

const toggleStatus = async () => {
    try {
        const action = props.task.status === 'running' ? 'stop' : 'start'
        await axios.post(`${API_URL}/tasks/${props.task.id}/${action}`)
        emit('refresh')
    } catch (e) {
        alert('Failed: ' + (e.response?.data?.message || e.message))
    }
}

const showLogs = async () => {
    showingLogs.value = true
    logs.value = 'Loading...'
    await refreshLogs()
    logInterval = setInterval(refreshLogs, 2000)
}

const showData = async () => {
    showingData.value = true
    resultData.value = null
    try {
        const res = await axios.get(`${API_URL}/tasks/${props.task.id}/data`)
        resultData.value = res.data.data
        if (Array.isArray(resultData.value) && resultData.value.length === 0) {
            resultData.value = null
        }
    } catch (e) {
        console.error(e)
    }
}

const refreshData = async () => {
    if (isRefreshing.value) return
    isRefreshing.value = true
    try {
        await axios.post(`${API_URL}/tasks/${props.task.id}/refresh`)
        const res = await axios.get(`${API_URL}/tasks/${props.task.id}/data`)
        resultData.value = res.data.data
        if (Array.isArray(resultData.value) && resultData.value.length === 0) {
            resultData.value = null
        }
    } catch (e) {
        alert('Failed: ' + (e.response?.data?.message || e.message))
    } finally {
        isRefreshing.value = false
    }
}

const clearLogs = async () => {
    if (!confirm('Clear logs?')) return
    try {
        await axios.delete(`${API_URL}/tasks/${props.task.id}/logs`)
        refreshLogs()
    } catch (e) {
        alert('Failed')
    }
}

const clearData = async () => {
    if (!confirm('Delete data?')) return
    try {
        await axios.delete(`${API_URL}/tasks/${props.task.id}/data`)
        resultData.value = null
    } catch (e) {
        alert('Failed')
    }
}

const closeLogs = () => {
    showingLogs.value = false
    if (logInterval) {
        clearInterval(logInterval)
        logInterval = null
    }
}

const refreshLogs = async () => {
    try {
        const res = await axios.get(`${API_URL}/tasks/${props.task.id}/logs`)
        const newLogs = res.data.data || "No logs available."

        const container = logContainer.value
        const isNearBottom = container ? (container.scrollHeight - Math.ceil(container.scrollTop) - container.clientHeight < 50) : true

        logs.value = newLogs

        if (isNearBottom) {
            nextTick(() => {
                if (logContainer.value) {
                    logContainer.value.scrollTop = logContainer.value.scrollHeight
                }
            })
        }
    } catch (e) {
        logs.value = "Failed to load logs."
    }
}

onUnmounted(() => {
    if (logInterval) clearInterval(logInterval)
})
</script>
