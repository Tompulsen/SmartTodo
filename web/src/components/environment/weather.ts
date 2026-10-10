export interface WeatherValues {
  time: number | null
  temperature_2m: number | null
  apparent_temperature: number | null
  relative_humidity_2m: number | null
  weather_code: number | null
  wind_speed_10m: number | null
}
export interface WeatherReply {
  timezone: string
  current: WeatherValues & { is_day: number | null; precipitation: number | null }
  hourly: (WeatherValues & { precipitation_probability: number | null; uv_index: number | null })[]
  daily: { time: number | null; temperature_2m_max: number | null; temperature_2m_min: number | null
    sunrise: number | null; sunset: number | null; precipitation_probability_max: number | null; uv_index_max: number | null }
  provider: string
}
export function weatherCondition(code: number | null, day = true) {
  if (code === null) return { label: '天气暂无数据', icon: 'cloud' }
  if (code === 0) return { label: day ? '晴' : '晴朗', icon: day ? 'sun' : 'moon' }
  if (code === 1 || code === 2) return { label: '多云', icon: 'cloud-sun' }
  if (code === 3) return { label: '阴', icon: 'cloud' }
  if ([45, 48].includes(code)) return { label: '雾', icon: 'mist' }
  if ([51, 53, 55, 56, 57].includes(code)) return { label: '毛毛雨', icon: 'rain' }
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return { label: '雨', icon: 'rain' }
  if ([71, 73, 75, 77, 85, 86].includes(code)) return { label: '雪', icon: 'snow' }
  if ([95, 96, 99].includes(code)) return { label: '雷雨', icon: 'storm' }
  return { label: '天气变化中', icon: 'cloud' }
}
export function comfort(value: WeatherValues) {
  const temp = value.apparent_temperature
  if (temp === null) return { label: '暂无体感数据', tone: 'neutral', detail: '天气数据更新后显示体感参考。' }
  if (temp < 10) return { label: '偏冷', tone: 'cool', detail: '外出增添衣物，把户外安排留给较温暖的时段。' }
  if (temp < 18) return { label: '微凉', tone: 'cool', detail: '适合搭配一件薄外套，注意室内外温差。' }
  if (temp >= 32) return { label: '炎热', tone: 'warm', detail: '减少高温时段的户外活动，留意当地高温预警。' }
  if (temp > 26) return { label: '偏暖', tone: 'warm', detail: '选择通风阴凉的环境，户外活动适当补水。' }
  if ((value.relative_humidity_2m ?? 50) > 75) return { label: '温和偏湿', tone: 'cool', detail: '温度温和，湿度较高，留意通风与室内湿度。' }
  if ((value.wind_speed_10m ?? 0) >= 8) return { label: '温和有风', tone: 'cool', detail: '气温温和但风力较大，外出留意天气变化。' }
  return { label: '温和舒适', tone: 'good', detail: '体感温度较温和，可以为散步或短暂休息留一点时间。' }
}
export function weatherTime(timestamp: number | null, timezone: string, date = false) {
  if (timestamp === null) return '--'
  return new Intl.DateTimeFormat('zh-CN', date
    ? { timeZone: timezone, month: 'long', day: 'numeric', weekday: 'long' }
    : { timeZone: timezone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(timestamp * 1000))
}
export function reading(value: number | null | undefined, decimals = 0) {
  return value == null || !Number.isFinite(value) ? '--' : value.toFixed(decimals)
}
export function locationError(error: { code: number }) {
  if (error.code === 1) return '未获得定位权限，暂时无法使用环境舒适度。请在浏览器的网站设置中允许定位后重试。'
  if (error.code === 3) return '定位超时，请确认设备定位已开启后重试。'
  return '暂时无法确定位置，请开启设备定位后重试。'
}
