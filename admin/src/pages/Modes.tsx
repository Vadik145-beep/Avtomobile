import { useEffect, useState } from 'react'
import {
  Card,
  Space,
  Typography,
  Alert,
  Spin,
  Table,
  Tag,
} from 'antd'
import type { TableColumnsType } from 'antd'
import dayjs from 'dayjs'
import client from '../api/client'

const { Title } = Typography

type Mode = 'exclusive' | 'speed' | 'coverage'

interface LogEntry {
  id: number
  mode: Mode
  speed_group_size: number
  updated_at: string
  updated_by: string
}

const modeLabels: Record<Mode, string> = {
  exclusive: 'Эксклюзив',
  speed: 'Скорость',
  coverage: 'Охват',
}

const modeColors: Record<Mode, string> = {
  exclusive: 'gold',
  speed: 'blue',
  coverage: 'green',
}

const logColumns: TableColumnsType<LogEntry> = [
  {
    title: 'Дата',
    dataIndex: 'updated_at',
    render: (v) => dayjs(v).format('DD.MM.YYYY HH:mm'),
    width: 160,
  },
  {
    title: 'Режим',
    dataIndex: 'mode',
    render: (v: Mode) => <Tag color={modeColors[v]}>{modeLabels[v]}</Tag>,
    width: 130,
  },
  {
    title: 'Размер группы',
    dataIndex: 'speed_group_size',
    width: 140,
    render: (v, row) => (row.mode === 'speed' ? v : '—'),
  },
  {
    title: 'Изменил',
    dataIndex: 'updated_by',
  },
]

export default function Modes() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [log, setLog] = useState<LogEntry[]>([])

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await client.get('/settings')
        if (Array.isArray(res.data.log)) {
          setLog(res.data.log)
        }
      } catch {
        setError('Не удалось загрузить настройки')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />
  if (error) return <Alert type="error" message={error} />

  return (
    <Space direction="vertical" size={24} style={{ width: '100%' }}>
      {log.length > 0 && (
        <Card title="Лог смен режима">
          <Table
            dataSource={log}
            columns={logColumns}
            rowKey="id"
            size="small"
            pagination={{ pageSize: 10 }}
          />
        </Card>
      )}

      {log.length === 0 && (
        <Card>
          <Title level={5} style={{ margin: 0, color: '#999' }}>
            История смен режима пуста
          </Title>
        </Card>
      )}
    </Space>
  )
}
