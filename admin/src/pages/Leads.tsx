import { useEffect, useState } from 'react'
import {
  Table,
  Tag,
  Typography,
  Spin,
  Alert,
  Space,
  Tooltip,
} from 'antd'
import type { TableColumnsType } from 'antd'
import dayjs from 'dayjs'
import client from '../api/client'

const { Text } = Typography

interface DeliveryInfo {
  status: 'sent' | 'opened' | 'blocked'
  username: string | null
  first_name: string | null
  telegram_id: number
  opened_at: string | null
}

interface LeadAdminOut {
  id: number
  call_id: string | null
  brand: string | null
  city: string | null
  phone: string | null
  created_at: string
  distribution_mode: string
  deliveries: DeliveryInfo[]
}

function getBuyerLabel(d: DeliveryInfo): string {
  if (d.username) return `@${d.username}`
  if (d.first_name) return d.first_name
  return `tg:${d.telegram_id}`
}

function LeadStatus({ deliveries }: { deliveries: DeliveryInfo[] }) {
  if (deliveries.length === 0) {
    return <Tag color="default">Не отправлен</Tag>
  }

  const opened = deliveries.filter((d) => d.status === 'opened')
  const sent = deliveries.filter((d) => d.status === 'sent')

  if (opened.length > 0) {
    return (
      <Space direction="vertical" size={2}>
        <Tag color="success">Открыт</Tag>
        {opened.map((d) => (
          <Tooltip
            key={d.telegram_id}
            title={d.opened_at ? `Открыт: ${dayjs(d.opened_at).format('DD.MM.YYYY HH:mm')}` : ''}
          >
            <Text style={{ fontSize: 12, color: '#52c41a' }}>
              {getBuyerLabel(d)}
            </Text>
          </Tooltip>
        ))}
      </Space>
    )
  }

  return (
    <Space direction="vertical" size={2}>
      <Tag color="processing">Отправлен</Tag>
      {sent.map((d) => (
        <Text key={d.telegram_id} style={{ fontSize: 12, color: '#1677ff' }}>
          {getBuyerLabel(d)}
        </Text>
      ))}
    </Space>
  )
}

const columns: TableColumnsType<LeadAdminOut> = [
  {
    title: 'Дата',
    dataIndex: 'created_at',
    width: 140,
    render: (v: string) => dayjs(v).format('DD.MM.YYYY HH:mm'),
    sorter: (a, b) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
    defaultSortOrder: 'descend',
  },
  {
    title: 'Марка / Город',
    width: 180,
    render: (_: unknown, r: LeadAdminOut) => (
      <Space direction="vertical" size={0}>
        <Text strong>{r.brand || '—'}</Text>
        <Text type="secondary" style={{ fontSize: 12 }}>{r.city || '—'}</Text>
      </Space>
    ),
  },
  {
    title: 'Телефон',
    dataIndex: 'phone',
    width: 150,
    render: (v: string | null) => v ? <Text copyable>{v}</Text> : <Text type="secondary">—</Text>,
  },
  {
    title: 'Режим',
    dataIndex: 'distribution_mode',
    width: 110,
    render: (v: string) => {
      const map: Record<string, { label: string; color: string }> = {
        coverage: { label: 'Охват', color: 'blue' },
        speed: { label: 'Скорость', color: 'orange' },
        exclusive: { label: 'Эксклюзив', color: 'purple' },
      }
      const item = map[v] ?? { label: v, color: 'default' }
      return <Tag color={item.color}>{item.label}</Tag>
    },
    filters: [
      { text: 'Охват', value: 'coverage' },
      { text: 'Скорость', value: 'speed' },
      { text: 'Эксклюзив', value: 'exclusive' },
    ],
    onFilter: (value, record) => record.distribution_mode === value,
  },
  {
    title: 'Статус / Покупатель',
    width: 200,
    render: (_: unknown, r: LeadAdminOut) => <LeadStatus deliveries={r.deliveries} />,
    filters: [
      { text: 'Не отправлен', value: 'none' },
      { text: 'Отправлен', value: 'sent' },
      { text: 'Открыт', value: 'opened' },
    ],
    onFilter: (value, record) => {
      if (value === 'none') return record.deliveries.length === 0
      if (value === 'opened') return record.deliveries.some((d) => d.status === 'opened')
      if (value === 'sent') return record.deliveries.length > 0 && !record.deliveries.some((d) => d.status === 'opened')
      return true
    },
  },
]

export default function Leads() {
  const [leads, setLeads] = useState<LeadAdminOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await client.get('/leads', { params: { limit: 200 } })
        setLeads(res.data)
      } catch {
        setError('Не удалось загрузить лиды')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />
  if (error) return <Alert type="error" message={error} />

  return (
    <Table
      dataSource={leads}
      columns={columns}
      rowKey="id"
      size="middle"
      pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `Всего: ${t}` }}
      locale={{ emptyText: 'Лидов пока нет' }}
    />
  )
}
