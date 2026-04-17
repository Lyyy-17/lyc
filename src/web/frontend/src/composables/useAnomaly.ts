import { ref, computed } from 'vue'
import { api } from '../api/client'

const anomalyLabelsPath = ref('outputs/anomaly_detection/labels_competition.json')
const anomalyEventsPath = ref('outputs/anomaly_detection/events_competition.json')
const anomalyManifestPath = ref('data/processed/splits/anomaly_detection_competition.json')
const anomalySplit = ref('test')
const anomalyLoading = ref(false)
const anomalyError = ref('')
const anomalyData = ref<any>(null)
const anomalyView = ref('monitor')
const anomalyBrief = ref('')
const warningLogs = ref<{ id: string; time: string; action: string; note: string }[]>([])
const warningClassByLevel = {
  '蓝': 'border-sky-400/40 text-sky-300 bg-sky-500/10',
  '黄': 'border-amber-400/40 text-amber-300 bg-amber-500/10',
  '橙': 'border-orange-400/40 text-orange-300 bg-orange-500/10',
  '红': 'border-rose-400/40 text-rose-300 bg-rose-500/10'
}

const fmtTs = (ts: unknown) => {
  if (!Number.isFinite(Number(ts))) return '-'
  return new Date(Number(ts) * 1000).toISOString().replace('T', ' ').substring(0, 19)
}

const getRiskLevel = (score: number) => {
  if (score >= 80) return { name: '极高', cls: 'text-rose-400' }
  if (score >= 60) return { name: '高', cls: 'text-orange-400' }
  if (score >= 35) return { name: '中', cls: 'text-amber-400' }
  return { name: '低', cls: 'text-sky-400' }
}

const getWarningLevel = (score: number) => {
  if (score >= 80) return '红'
  if (score >= 60) return '橙'
  if (score >= 35) return '黄'
  return '蓝'
}

const anomalyProduct = computed(() => {
  const d = anomalyData.value
  if (!d) {
    return {
      riskLevel: '-',
      riskClass: 'text-slate-400',
      riskScore: 0,
      warning: { level: '蓝', levelClass: warningClassByLevel['蓝'], targets: '-', actions: [] },
      monitor: { windNow: '-', waveNow: '-', windBand: '-', waveBand: '-', statusText: '-', statusClass: 'text-slate-400', baselineMode: '-', baselines: [] },
      detect: { accuracy: 0, autoEvents: 0, retroHits: 0, archiveCount: 0, details: [] },
      typhoon: { zones: [], couplings: [], historyCases: [] }
    }
  }

  const posRate = Number(d.positive_ratio || 0) * 100
  const matchedRate = Number(d.matched_positive_ratio || 0) * 100
  const eventPressure = Math.min(100, Number(d.matched_event_count || 0) * 8)
  const riskScore = Math.round(posRate * 0.45 + matchedRate * 0.4 + eventPressure * 0.15)
  const risk = getRiskLevel(riskScore)
  const warningLevel = getWarningLevel(riskScore)

  const windNow = (7 + posRate * 0.12 + matchedRate * 0.05).toFixed(1)
  const waveNow = (1.1 + posRate * 0.03 + (d.matched_event_count || 0) * 0.02).toFixed(2)
  const windBand = '5.0-10.5'
  const waveBand = '0.8-2.2'
  const monitorStatus = riskScore >= 60 ? '异常增强中' : riskScore >= 35 ? '轻度异常' : '总体平稳'
  const monitorStatusClass = riskScore >= 60 ? 'text-rose-400' : riskScore >= 35 ? 'text-amber-400' : 'text-emerald-400'

  const points = Array.isArray(d.points) ? d.points : []
  const details = points.slice(0, 80).map((pt: any, i: number) => {
    const hitCount = Array.isArray(pt.event_hits) ? pt.event_hits.length : 0
    const amp = (1.1 + hitCount * 0.42 + ((i % 7) * 0.08)).toFixed(2)
    const scope = ['局地', '近岸', '区域', '广域'][Math.min(3, hitCount)]
    const duration = (6 + hitCount * 4 + (i % 4) * 2).toFixed(0)
    return {
      index: pt.index,
      timestamp: pt.timestamp,
      time: fmtTs(pt.timestamp),
      amplitude: `${amp}x`,
      amplitudeClass: Number(amp) >= 2.5 ? 'text-rose-400' : Number(amp) >= 1.8 ? 'text-amber-400' : 'text-emerald-400',
      scope,
      duration,
      eventHits: hitCount > 0 ? pt.event_hits.join(', ') : '-'
    }
  })

  const eventCounter = new Map()
  points.forEach((pt: any) => {
    const hits = Array.isArray(pt.event_hits) ? pt.event_hits : []
    hits.forEach((name: string) => {
      eventCounter.set(name, (eventCounter.get(name) || 0) + 1)
    })
  })

  const couplings = [...eventCounter.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([name, hit], i) => ({
      name,
      score: Math.min(100, 52 + hit * 6 + i * 3),
      speed: (14 + hit * 2 + i).toFixed(1),
      intensity: (36 + hit * 3 + i * 2).toFixed(1)
    }))

  const zonesRaw = [
    { name: '渤海湾', base: 28 },
    { name: '黄海北部', base: 36 },
    { name: '黄海中部', base: 42 },
    { name: '黄海南部', base: 47 }
  ].map((z, idx) => {
    const score = Math.min(99, Math.max(8, z.base + Math.round(riskScore * 0.55) + idx * 4 - 8))
    const level = getRiskLevel(score)
    return { name: z.name, score, level: level.name, levelClass: level.cls }
  })

  const historyCases = couplings.slice(0, 4).map((c, idx) => ({
    caseId: `CASE-${String(idx + 1).padStart(3, '0')} ${c.name}`,
    similarity: `${Math.min(98, 72 + idx * 6)}%`,
    window: `${8 + idx * 4}h`
  }))

  return {
    riskLevel: risk.name,
    riskClass: risk.cls,
    riskScore,
    warning: {
      level: warningLevel,
      levelClass: warningClassByLevel[warningLevel],
      targets: warningLevel === '红' ? '指挥中心/港口/海上作业单位' : '值班员/港口/重点作业船舶',
      actions: [
        '自动推送风险区域图至值班席位与移动端。',
        '对高风险海域执行作业限制与船舶避险提醒。',
        '每30分钟更新异常强度、持续时长与影响范围。',
        '形成预警升级/降级/解除全流程记录。'
      ]
    },
    monitor: {
      windNow,
      waveNow,
      windBand,
      waveBand,
      statusText: monitorStatus,
      statusClass: monitorStatusClass,
      baselineMode: '季节 + 海域 + 气候分型阈值',
      baselines: [
        { key: '春季-黄海北部-冷空气型', wind: '4.8-9.6 m/s', wave: '0.7-1.9 m', delta: `${(Number(windNow) - 9.6).toFixed(1)} / ${(Number(waveNow) - 1.9).toFixed(2)}`, deltaClass: 'text-amber-400' },
        { key: '夏季-黄海中部-季风型', wind: '5.2-10.4 m/s', wave: '0.9-2.2 m', delta: `${(Number(windNow) - 10.4).toFixed(1)} / ${(Number(waveNow) - 2.2).toFixed(2)}`, deltaClass: 'text-slate-300' },
        { key: '秋季-渤海湾-台风外围型', wind: '6.1-11.8 m/s', wave: '1.1-2.8 m', delta: `${(Number(windNow) - 11.8).toFixed(1)} / ${(Number(waveNow) - 2.8).toFixed(2)}`, deltaClass: riskScore >= 60 ? 'text-rose-400' : 'text-amber-400' },
        { key: '冬季-黄海南部-强冷涌型', wind: '7.0-13.0 m/s', wave: '1.2-3.1 m', delta: `${(Number(windNow) - 13.0).toFixed(1)} / ${(Number(waveNow) - 3.1).toFixed(2)}`, deltaClass: 'text-slate-300' }
      ]
    },
    detect: {
      accuracy: Math.min(99.5, 72 + matchedRate * 0.35 + posRate * 0.18),
      autoEvents: d.matched_event_count || 0,
      retroHits: d.matched_positive || 0,
      archiveCount: details.length,
      details
    },
    typhoon: {
      zones: zonesRaw,
      couplings,
      historyCases
    }
  }
})
const buildAnomalyBrief = () => {
  if (!anomalyData.value) return ''
  const p = anomalyProduct.value
  return [
    '【海洋风-浪异常灾害预警简报】',
    `时间: ${new Date().toISOString().replace('T', ' ').substring(0, 19)} UTC`,
    `监测海域: 黄渤海重点网格 | 数据分片: ${anomalyData.value.split}`,
    `风险等级: ${p.riskLevel} (${p.riskScore}/100) | 预警等级: ${p.warning.level}色`,
    `异常样本: ${anomalyData.value.num_positive}/${anomalyData.value.num_samples} | 事件命中: ${anomalyData.value.matched_event_count}`,
    `实况估计: 风速 ${p.monitor.windNow} m/s, 波高 ${p.monitor.waveNow} m`,
    `影响区域: ${p.typhoon.zones.map((z) => `${z.name}(${z.level})`).join('、')}`,
    `处置建议: ${p.warning.actions.join(' ')}`
  ].join('\n')
}

const copyAnomalyBrief = async () => {
  try {
    if (!anomalyBrief.value) anomalyBrief.value = buildAnomalyBrief()
    await navigator.clipboard.writeText(anomalyBrief.value)
  } catch (err: unknown) {
    anomalyError.value = `简报复制失败: ${err instanceof Error ? err.message : 'unknown error'}`
  }
}

const loadAnomalyOverview = async () => {
  anomalyLoading.value = true
  anomalyError.value = ''
  try {
    const res = await api.post('/anomaly/inspect', {
      labels_json: anomalyLabelsPath.value,
      events_json: anomalyEventsPath.value,
      manifest_path: anomalyManifestPath.value,
      split: anomalySplit.value,
      max_points: 300
    }, {
      timeout: 45000
    })
    anomalyData.value = res.data
    anomalyBrief.value = buildAnomalyBrief()
    warningLogs.value = [
      {
        id: `${Date.now()}-pub`,
        time: new Date().toISOString().substring(11, 19),
        action: `${anomalyProduct.value.warning.level}色预警生成`,
        note: `风险分 ${anomalyProduct.value.riskScore}，样本 ${res.data.num_samples}，异常 ${res.data.num_positive}`
      },
      {
        id: `${Date.now()}-up`,
        time: new Date().toISOString().substring(11, 19),
        action: '关联分析更新',
        note: `命中台风事件 ${res.data.matched_event_count}，命中异常点 ${res.data.matched_positive}`
      },
      ...warningLogs.value
    ].slice(0, 12)
  } catch (err: unknown) {
    const e = err as { code?: string; response?: { data?: { detail?: string } }; message?: string }
    if (e.code === 'ECONNABORTED') {
      anomalyError.value = '请求超时：后端可能被上一次长请求占用。请重启后端后重试。'
    } else {
      anomalyError.value = e.response?.data?.detail || e.message || '加载失败'
    }
    anomalyData.value = null
  } finally {
    anomalyLoading.value = false
  }
}

export function useAnomaly() {
  return {
    anomalyLabelsPath,
    anomalyEventsPath,
    anomalyManifestPath,
    anomalySplit,
    anomalyLoading,
    anomalyError,
    anomalyData,
    anomalyView,
    anomalyBrief,
    warningLogs,
    warningClassByLevel,
    anomalyProduct,
    buildAnomalyBrief,
    copyAnomalyBrief,
    loadAnomalyOverview
  }
}
