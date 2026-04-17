<template>
<section class="h-full flex gap-6">
        <aside class="w-[380px] glass-panel flex flex-col h-full shrink-0 p-5 gap-4 overflow-y-auto custom-scrollbar">
          <h2 class="panel-title"><ShieldAlert class="w-5 h-5 text-tech-cyan" /> ANOMALY INSPECTOR</h2>

          <div class="space-y-2">
            <label class="text-[10px] font-mono text-slate-400 uppercase tracking-widest">Labels JSON</label>
            <input type="text" v-model="anomalyLabelsPath" class="tech-input" />
          </div>

          <div class="space-y-2">
            <label class="text-[10px] font-mono text-slate-400 uppercase tracking-widest">Events JSON</label>
            <input type="text" v-model="anomalyEventsPath" class="tech-input" />
          </div>

          <div class="space-y-2">
            <label class="text-[10px] font-mono text-slate-400 uppercase tracking-widest">Manifest JSON</label>
            <input type="text" v-model="anomalyManifestPath" class="tech-input" />
          </div>

          <div class="space-y-2">
            <label class="text-[10px] font-mono text-slate-400 uppercase tracking-widest">Split</label>
            <select v-model="anomalySplit" class="tech-input">
              <option value="train">train</option>
              <option value="val">val</option>
              <option value="test">test</option>
            </select>
          </div>

          <button class="tech-btn primary-btn w-full flex items-center justify-center gap-2" @click="loadAnomalyOverview">
            <Search class="w-4 h-4" /> LOAD LABELS & HITS
          </button>

          <p v-if="anomalyError" class="text-xs text-rose-400 font-mono leading-relaxed">{{ anomalyError }}</p>
          <p v-if="anomalyLoading" class="text-xs text-tech-cyan font-mono animate-pulse">LOADING ANOMALY POINTS...</p>
        </aside>

        <main class="flex-1 glass-panel p-5 overflow-hidden flex flex-col min-w-0">
          <div class="flex items-center justify-between gap-3 mb-4">
            <div class="flex items-center gap-3">
              <Database class="w-5 h-5 text-tech-cyan" />
              <h2 class="font-display text-lg tracking-widest text-white m-0">风-浪异常智能识别与灾害预警</h2>
            </div>
            <div v-if="anomalyProduct" class="px-3 py-1 rounded border text-[11px] font-mono"
              :class="anomalyProduct.warning.levelClass">
              {{ anomalyProduct.warning.level }}预警 | 风险分 {{ anomalyProduct.riskScore }}
            </div>
          </div>

          <div v-if="!anomalyData" class="flex-1 flex items-center justify-center text-slate-500 font-mono text-sm tracking-widest">
            请先加载 labels/events
          </div>

          <template v-else>
            <div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-4">
              <div class="p-3 rounded-lg bg-slate-900/60 border border-slate-700">
                <div class="text-[10px] text-slate-400 font-mono">SAMPLES</div>
                <div class="text-xl text-white font-mono">{{ anomalyData.num_samples }}</div>
              </div>
              <div class="p-3 rounded-lg bg-slate-900/60 border border-slate-700">
                <div class="text-[10px] text-slate-400 font-mono">POSITIVE</div>
                <div class="text-xl text-amber-400 font-mono">{{ anomalyData.num_positive }}</div>
              </div>
              <div class="p-3 rounded-lg bg-slate-900/60 border border-slate-700">
                <div class="text-[10px] text-slate-400 font-mono">MATCHED_POSITIVE</div>
                <div class="text-xl text-emerald-400 font-mono">{{ anomalyData.matched_positive }}</div>
              </div>
              <div class="p-3 rounded-lg bg-slate-900/60 border border-slate-700">
                <div class="text-[10px] text-slate-400 font-mono">EVENTS_HIT</div>
                <div class="text-xl text-tech-cyan font-mono">{{ anomalyData.matched_event_count }}</div>
              </div>
              <div class="p-3 rounded-lg bg-slate-900/60 border border-slate-700">
                <div class="text-[10px] text-slate-400 font-mono">RISK_LEVEL</div>
                <div class="text-xl font-mono" :class="anomalyProduct.riskClass">{{ anomalyProduct.riskLevel }}</div>
              </div>
            </div>

            <div class="text-xs text-slate-400 font-mono mb-2">
              split={{ anomalyData.split }} | positive_ratio={{ (anomalyData.positive_ratio * 100).toFixed(2) }}% | matched_positive_ratio={{ (anomalyData.matched_positive_ratio * 100).toFixed(2) }}%
            </div>

            <div class="flex items-center gap-2 mb-3">
              <button class="px-3 py-1.5 rounded-md text-xs font-mono border transition-all"
                :class="anomalyView === 'monitor' ? 'border-tech-cyan bg-tech-cyan/10 text-tech-cyan' : 'border-slate-700 text-slate-400 hover:text-slate-200'"
                @click="anomalyView = 'monitor'">1. 实况监测与基准</button>
              <button class="px-3 py-1.5 rounded-md text-xs font-mono border transition-all"
                :class="anomalyView === 'detect' ? 'border-tech-cyan bg-tech-cyan/10 text-tech-cyan' : 'border-slate-700 text-slate-400 hover:text-slate-200'"
                @click="anomalyView = 'detect'">2. 异常识别与回溯</button>
              <button class="px-3 py-1.5 rounded-md text-xs font-mono border transition-all"
                :class="anomalyView === 'typhoon' ? 'border-tech-cyan bg-tech-cyan/10 text-tech-cyan' : 'border-slate-700 text-slate-400 hover:text-slate-200'"
                @click="anomalyView = 'typhoon'">3. 台风关联与评估</button>
              <button class="px-3 py-1.5 rounded-md text-xs font-mono border transition-all"
                :class="anomalyView === 'warning' ? 'border-tech-cyan bg-tech-cyan/10 text-tech-cyan' : 'border-slate-700 text-slate-400 hover:text-slate-200'"
                @click="anomalyView = 'warning'">4. 分级预警发布</button>
            </div>

            <div v-if="anomalyView === 'monitor'" class="flex-1 overflow-auto custom-scrollbar space-y-3">
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div class="p-4 rounded-lg border border-slate-700 bg-slate-900/60">
                  <div class="text-[10px] font-mono text-slate-400">实时风速估计 (m/s)</div>
                  <div class="text-2xl font-mono text-white mt-1">{{ anomalyProduct.monitor.windNow }}</div>
                  <div class="text-[11px] font-mono text-slate-400 mt-1">基准区间 {{ anomalyProduct.monitor.windBand }}</div>
                </div>
                <div class="p-4 rounded-lg border border-slate-700 bg-slate-900/60">
                  <div class="text-[10px] font-mono text-slate-400">实时波高估计 (m)</div>
                  <div class="text-2xl font-mono text-white mt-1">{{ anomalyProduct.monitor.waveNow }}</div>
                  <div class="text-[11px] font-mono text-slate-400 mt-1">基准区间 {{ anomalyProduct.monitor.waveBand }}</div>
                </div>
                <div class="p-4 rounded-lg border border-slate-700 bg-slate-900/60">
                  <div class="text-[10px] font-mono text-slate-400">24H 监测状态</div>
                  <div class="text-lg font-mono mt-2" :class="anomalyProduct.monitor.statusClass">{{ anomalyProduct.monitor.statusText }}</div>
                  <div class="text-[11px] font-mono text-slate-400 mt-1">阈值模式: {{ anomalyProduct.monitor.baselineMode }}</div>
                </div>
              </div>

              <div class="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                <div class="text-xs font-mono text-slate-300 mb-2">基准模式对比 (按季节/海域/气候)</div>
                <table class="w-full text-xs font-mono">
                  <thead class="bg-slate-900 text-slate-300">
                    <tr>
                      <th class="text-left p-2 border-b border-slate-800">维度</th>
                      <th class="text-left p-2 border-b border-slate-800">风速基准</th>
                      <th class="text-left p-2 border-b border-slate-800">波高基准</th>
                      <th class="text-left p-2 border-b border-slate-800">偏离</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in anomalyProduct.monitor.baselines" :key="row.key" class="odd:bg-slate-900/30">
                      <td class="p-2 border-b border-slate-800/60">{{ row.key }}</td>
                      <td class="p-2 border-b border-slate-800/60">{{ row.wind }}</td>
                      <td class="p-2 border-b border-slate-800/60">{{ row.wave }}</td>
                      <td class="p-2 border-b border-slate-800/60" :class="row.deltaClass">{{ row.delta }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div v-else-if="anomalyView === 'detect'" class="flex-1 overflow-auto custom-scrollbar space-y-3">
              <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div class="p-3 rounded-lg bg-slate-900/60 border border-slate-700">
                  <div class="text-[10px] font-mono text-slate-400">异常识别准确率(估计)</div>
                  <div class="text-xl font-mono" :class="anomalyProduct.detect.accuracy >= 80 ? 'text-emerald-400' : 'text-amber-400'">{{ anomalyProduct.detect.accuracy.toFixed(2) }}%</div>
                </div>
                <div class="p-3 rounded-lg bg-slate-900/60 border border-slate-700">
                  <div class="text-[10px] font-mono text-slate-400">自动识别事件</div>
                  <div class="text-xl text-white font-mono">{{ anomalyProduct.detect.autoEvents }}</div>
                </div>
                <div class="p-3 rounded-lg bg-slate-900/60 border border-slate-700">
                  <div class="text-[10px] font-mono text-slate-400">历史回溯命中</div>
                  <div class="text-xl text-tech-cyan font-mono">{{ anomalyProduct.detect.retroHits }}</div>
                </div>
                <div class="p-3 rounded-lg bg-slate-900/60 border border-slate-700">
                  <div class="text-[10px] font-mono text-slate-400">可归档案例</div>
                  <div class="text-xl text-white font-mono">{{ anomalyProduct.detect.archiveCount }}</div>
                </div>
              </div>

              <div class="border border-slate-800 rounded-lg overflow-auto custom-scrollbar">
                <table class="w-full text-xs font-mono">
                  <thead class="sticky top-0 bg-slate-900 text-slate-300">
                    <tr>
                      <th class="text-left p-2 border-b border-slate-800">index</th>
                      <th class="text-left p-2 border-b border-slate-800">time</th>
                      <th class="text-left p-2 border-b border-slate-800">异常幅度</th>
                      <th class="text-left p-2 border-b border-slate-800">影响范围</th>
                      <th class="text-left p-2 border-b border-slate-800">持续时长(h)</th>
                      <th class="text-left p-2 border-b border-slate-800">event_hits</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="ev in anomalyProduct.detect.details" :key="`${ev.index}-${ev.timestamp}`" class="odd:bg-slate-900/30">
                      <td class="p-2 border-b border-slate-800/60">{{ ev.index }}</td>
                      <td class="p-2 border-b border-slate-800/60">{{ ev.time }}</td>
                      <td class="p-2 border-b border-slate-800/60" :class="ev.amplitudeClass">{{ ev.amplitude }}</td>
                      <td class="p-2 border-b border-slate-800/60">{{ ev.scope }}</td>
                      <td class="p-2 border-b border-slate-800/60">{{ ev.duration }}</td>
                      <td class="p-2 border-b border-slate-800/60">{{ ev.eventHits }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div v-else-if="anomalyView === 'typhoon'" class="flex-1 overflow-auto custom-scrollbar space-y-3">
              <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
                <div class="p-3 rounded-lg bg-slate-900/60 border border-slate-700" v-for="zone in anomalyProduct.typhoon.zones" :key="zone.name">
                  <div class="text-[10px] font-mono text-slate-400">{{ zone.name }}</div>
                  <div class="text-xl font-mono mt-1" :class="zone.levelClass">{{ zone.level }}</div>
                  <div class="text-[11px] font-mono text-slate-400">影响度 {{ zone.score }}</div>
                </div>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div class="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                  <div class="text-xs font-mono text-slate-300 mb-2">台风-风浪耦合关系 Top</div>
                  <div class="space-y-2">
                    <div v-for="item in anomalyProduct.typhoon.couplings" :key="item.name" class="p-2 rounded border border-slate-800 bg-slate-900/50">
                      <div class="flex items-center justify-between text-xs font-mono">
                        <span class="text-tech-cyan">{{ item.name }}</span>
                        <span class="text-slate-300">耦合度 {{ item.score }}</span>
                      </div>
                      <div class="text-[11px] font-mono text-slate-400 mt-1">路径速度 {{ item.speed }} kt | 强度 {{ item.intensity }} kt</div>
                    </div>
                  </div>
                </div>

                <div class="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                  <div class="text-xs font-mono text-slate-300 mb-2">历史相似案例库</div>
                  <div class="space-y-2">
                    <div v-for="c in anomalyProduct.typhoon.historyCases" :key="c.caseId" class="p-2 rounded border border-slate-800 bg-slate-900/50">
                      <div class="text-xs font-mono text-white">{{ c.caseId }}</div>
                      <div class="text-[11px] font-mono text-slate-400">相似度 {{ c.similarity }} | 事件窗口 {{ c.window }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="flex-1 overflow-auto custom-scrollbar space-y-3">
              <div class="p-4 rounded-lg border bg-slate-900/50" :class="anomalyProduct.warning.levelClass">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <div class="text-[10px] font-mono opacity-80">国家海洋灾害预警标准映射</div>
                    <div class="text-xl font-mono mt-1">当前: {{ anomalyProduct.warning.level }}色预警</div>
                  </div>
                  <div class="text-right text-xs font-mono opacity-80">
                    风险等级 {{ anomalyProduct.riskLevel }}<br />
                    推送对象 {{ anomalyProduct.warning.targets }}
                  </div>
                </div>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div class="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                  <div class="text-xs font-mono text-slate-300 mb-2">预警处置建议</div>
                  <ul class="space-y-2 text-xs font-mono text-slate-300">
                    <li v-for="advice in anomalyProduct.warning.actions" :key="advice" class="p-2 rounded bg-slate-900/50 border border-slate-800">{{ advice }}</li>
                  </ul>
                </div>

                <div class="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                  <div class="text-xs font-mono text-slate-300 mb-2">预警流程留痕</div>
                  <div class="space-y-2 text-xs font-mono">
                    <div v-for="log in warningLogs" :key="log.id" class="p-2 rounded border border-slate-800 bg-slate-900/50">
                      <div class="text-slate-200">{{ log.time }} | {{ log.action }}</div>
                      <div class="text-slate-400">{{ log.note }}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                <div class="flex items-center justify-between mb-2">
                  <div class="text-xs font-mono text-slate-300">标准化预警简报</div>
                  <button class="px-3 py-1 rounded border border-tech-cyan/40 text-tech-cyan text-[11px] font-mono hover:bg-tech-cyan/10" @click="copyAnomalyBrief">复制简报</button>
                </div>
                <textarea v-model="anomalyBrief" class="w-full h-36 tech-input !leading-6" />
              </div>
            </div>

            <div v-if="anomalyData.truncated" class="mt-2 text-[10px] text-amber-400 font-mono">结果已截断显示，请提高后端 max_points。</div>
          </template>
        </main>
      </section>
</template>

<script setup>
import { ShieldAlert, Search, Database } from 'lucide-vue-next'
import { useAnomaly } from '../../composables/useAnomaly'

const {
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
  anomalyProduct,
  loadAnomalyOverview,
  copyAnomalyBrief
} = useAnomaly()
</script>
