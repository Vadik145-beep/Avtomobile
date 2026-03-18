import { useEffect, useState } from 'react'
import {
  Card,
  Row,
  Col,
  Button,
  Select,
  Space,
  Typography,
  Statistic,
  Alert,
  Spin,
  DatePicker,
  Table,
} from 'antd'
import type { TableColumnsType } from 'antd'
import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import dayjs, { Dayjs } from 'dayjs'
import client from '../api/client'

const { RangePicker } = DatePicker
const { Title, Text } = Typography

type ModeFilter = 'all' | 'exclusive' | 'speed' | 'coverage'

interface DailyPoint {
  date: string
  leads_sent: number
  leads_opened: number
  conversion: number
}

interface AnalyticsData {
  total_sent: number
  total_opened: number
  avg_conversion: number
  daily: DailyPoint[]
}

const modeOptions = [
  { value: 'all', label: 'Все режимы' },
  { value: 'exclusive', label: 'Эксклюзив' },
  { value: 'speed', label: 'Скорость' },
  { value: 'coverage', label: 'Охват' },
]

const dailyColumns: TableColumnsType<DailyPoint> = [
  {
    title: 'Дата',
    dataIndex: 'date',
    render: (v) => dayjs(v).format('DD.MM.YYYY'),
    width: 120,
  },
  { title: 'Отправлено', dataIndex: 'leads_sent', width: 120 },
  { title: 'Открыто', dataIndex: 'leads_opened', width: 120 },
  {
    title: 'Конверсия',
    dataIndex: 'conversion',
    render: (v) => `${(v * 100).toFixed(1)}%`,
    width: 120,
  },
]

function exportCsv(data: DailyPoint[]) {
  const header = 'Дата,Отправлено,Открыто,Конверсия'
  const rows = data.map((d) =>
    [dayjs(d.date).format('DD.MM.YYYY'), d.leads_sent, d.leads_opened, `${(d.conversion * 100).toFixed(1)}%`].join(',')
  )
  const csv = [header, ...rows].join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `avto-lead-analytics-${dayjs().format('YYYYMMDD')}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(29, 'day'),
    dayjs(),
  ])
  const [modeFilter, setModeFilter] = useState<ModeFilter>('all')

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string> = {
        date_from: dateRange[0].format('YYYY-MM-DD'),
        date_to: dateRange[1].format('YYYY-MM-DD'),
      }
      if (modeFilter !== 'all') params.mode = modeFilter

      const res = await client.get('/stats', { params: { ...params, analytics: '1' } })
      const raw = res.data

      const daily: DailyPoint[] = (raw.daily ?? []).map((d: DailyPoint) => ({
        ...d,
        conversion:
          d.leads_sent > 0 ? d.leads_opened / d.leads_sent : 0,
      }))

      const totalSent = daily.reduce((s, d) => s + d.leads_sent, 0)
      const totalOpened = daily.reduce((s, d) => s + d.leads_opened, 0)

      setData({
        total_sent: raw.total_sent ?? totalSent,
        total_opened: raw.total_opened ?? totalOpened,
        avg_conversion: totalSent > 0 ? totalOpened / totalSent : 0,
        daily,
      })
    } catch {
      setError('Не удалось загрузить аналитику')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />
  if (error) return <Alert type="error" message={error} />

  const chartData = (data?.daily ?? []).map((d) => ({
    ...d,
    date: dayjs(d.date).format('DD.MM'),
    conversion_pct: +(d.conversion * 100).toFixed(1),
  }))

  return (
    <Space direction="vertical" size={20} style={{ width: '100%' }}>
      <Row gutter={12} align="middle" wrap>
        <Col>
          <RangePicker
            value={dateRange}
            onChange={(v) => v && setDateRange(v as [Dayjs, Dayjs])}
            format="DD.MM.YYYY"
            allowClear={false}
          />
        </Col>
        <Col>
          <Select
            value={modeFilter}
            onChange={setModeFilter}
            options={modeOptions}
            style={{ width: 160 }}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={load} type="primary">
            Применить
          </Button>
        </Col>
        <Col flex="auto" />
        <Col>
          <Button
            icon={<DownloadOutlined />}
            onClick={() => exportCsv(data?.daily ?? [])}
            disabled={!data?.daily?.length}
          >
            Экспорт CSV
          </Button>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="Лидов отправлено" value={data?.total_sent ?? 0} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="Контактов открыто" value={data?.total_opened ?? 0} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Средняя конверсия"
              value={((data?.avg_conversion ?? 0) * 100).toFixed(1)}
              suffix="%"
              valueStyle={{ color: (data?.avg_conversion ?? 0) > 0.3 ? '#52c41a' : '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Card title="Конверсия по дням (анонс → открытие контакта)">
        {chartData.length === 0 ? (
          <Text type="secondary">Нет данных за выбранный период</Text>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis yAxisId="left" allowDecimals={false} />
              <YAxis yAxisId="right" orientation="right" unit="%" domain={[0, 100]} />
              <Tooltip
                formatter={(value, name) =>
                  name === 'Конверсия %' ? [`${value}%`, name] : [value, name]
                }
              />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="leads_sent"
                name="Отправлено"
                stroke="#1677ff"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="leads_opened"
                name="Открыто"
                stroke="#52c41a"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="conversion_pct"
                name="Конверсия %"
                stroke="#fa8c16"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>

      {(data?.daily?.length ?? 0) > 0 && (
        <Card title="Детализация по дням">
          <Table
            dataSource={data?.daily ?? []}
            columns={dailyColumns}
            rowKey="date"
            size="small"
            pagination={{ pageSize: 14, showSizeChanger: false }}
          />
        </Card>
      )}
    </Space>
  )
}
