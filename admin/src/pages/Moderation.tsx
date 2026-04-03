import { useEffect, useState } from 'react'
import {
  Table,
  Tag,
  Typography,
  Spin,
  Alert,
  Space,
  Button,
  Tooltip,
  message,
  Badge,
  Modal,
  Form,
  Input,
  Select,
  Switch,
} from 'antd'
import { CheckOutlined, CloseOutlined, PlusOutlined } from '@ant-design/icons'
import type { TableColumnsType } from 'antd'
import dayjs from 'dayjs'
import client from '../api/client'

const { Text } = Typography

interface LeadPending {
  id: number
  call_id: string | null
  client_name: string | null
  country_origin: string | null
  timing: string | null
  city: string | null
  phone: string | null
  created_at: string
  distribution_mode: string
  is_test: boolean
  moderation_status: string
}

interface LeadCreateValues {
  phone: string
  client_name?: string
  country_origin?: string
  timing?: string
  city?: string
  summary?: string
  distribution_mode: 'coverage' | 'speed' | 'exclusive'
  is_test: boolean
}

export default function Moderation() {
  const [leads, setLeads] = useState<LeadPending[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [processingIds, setProcessingIds] = useState<Set<number>>(new Set())
  const [modalOpen, setModalOpen] = useState(false)
  const [formLoading, setFormLoading] = useState(false)
  const [form] = Form.useForm<LeadCreateValues>()

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await client.get('/leads', {
        params: { limit: 200, moderation_status: 'pending' },
      })
      setLeads(res.data)
    } catch {
      setError('Не удалось загрузить лиды на модерацию')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleApprove = async (id: number) => {
    setProcessingIds((prev) => new Set(prev).add(id))
    try {
      await client.post(`/leads/${id}/approve`)
      setLeads((prev) => prev.filter((l) => l.id !== id))
      message.success('Лид одобрен и отправлен в рассылку')
    } catch {
      message.error('Не удалось одобрить лид')
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  const handleReject = async (id: number) => {
    setProcessingIds((prev) => new Set(prev).add(id))
    try {
      await client.post(`/leads/${id}/reject`)
      setLeads((prev) => prev.filter((l) => l.id !== id))
      message.success('Лид отклонён')
    } catch {
      message.error('Не удалось отклонить лид')
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  const handleCreate = async (values: LeadCreateValues) => {
    setFormLoading(true)
    try {
      const res = await client.post('/leads', { ...values, pending_moderation: true })
      setLeads((prev) => [res.data, ...prev])
      message.success('Лид добавлен на модерацию')
      setModalOpen(false)
      form.resetFields()
    } catch {
      message.error('Не удалось добавить лид')
    } finally {
      setFormLoading(false)
    }
  }

  const columns: TableColumnsType<LeadPending> = [
    {
      title: 'Дата',
      dataIndex: 'created_at',
      width: 140,
      render: (v: string) => dayjs(v).format('DD.MM.YYYY HH:mm'),
      sorter: (a, b) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
      defaultSortOrder: 'descend',
    },
    {
      title: 'Клиент / Город',
      width: 180,
      render: (_: unknown, r: LeadPending) => (
        <Space direction="vertical" size={0}>
          <Space size={4}>
            <Text strong>{r.client_name || '—'}</Text>
            {r.is_test && (
              <Tag color="red" style={{ marginLeft: 4 }}>
                Тест
              </Tag>
            )}
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {r.city || '—'}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Страна / Сроки',
      width: 150,
      render: (_: unknown, r: LeadPending) => (
        <Space direction="vertical" size={0}>
          <Text>{r.country_origin || '—'}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {r.timing || '—'}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Телефон',
      dataIndex: 'phone',
      width: 150,
      render: (v: string | null) =>
        v ? <Text copyable>{v}</Text> : <Text type="secondary">—</Text>,
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
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 120,
      render: (_: unknown, r: LeadPending) => (
        <Space>
          <Tooltip title="Одобрить — отправить в Лиды и в Telegram">
            <Button
              type="primary"
              shape="circle"
              icon={<CheckOutlined />}
              loading={processingIds.has(r.id)}
              onClick={() => handleApprove(r.id)}
              style={{ background: '#52c41a', borderColor: '#52c41a' }}
            />
          </Tooltip>
          <Tooltip title="Отклонить">
            <Button
              danger
              shape="circle"
              icon={<CloseOutlined />}
              loading={processingIds.has(r.id)}
              onClick={() => handleReject(r.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />
  if (error) return <Alert type="error" message={error} />

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Badge count={leads.length} overflowCount={999} color="#faad14">
            <Text strong style={{ fontSize: 15 }}>
              Лиды на проверке
            </Text>
          </Badge>
          <Button size="small" onClick={load}>
            Обновить
          </Button>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          Добавить лид
        </Button>
      </div>

      <Table
        dataSource={leads}
        columns={columns}
        rowKey="id"
        size="middle"
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `Всего: ${t}` }}
        locale={{ emptyText: 'Нет лидов на модерации' }}
      />

      <Modal
        title="Добавить лид на модерацию"
        open={modalOpen}
        onCancel={() => { setModalOpen(false); form.resetFields() }}
        onOk={() => form.submit()}
        okText="Добавить"
        cancelText="Отмена"
        confirmLoading={formLoading}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{ distribution_mode: 'coverage', is_test: false }}
        >
          <Form.Item
            name="phone"
            label="Телефон"
            rules={[{ required: true, message: 'Введите номер телефона' }]}
          >
            <Input placeholder="+7 999 123 45 67" />
          </Form.Item>
          <Form.Item name="client_name" label="Имя клиента">
            <Input placeholder="Иван" />
          </Form.Item>
          <Form.Item name="country_origin" label="Страна">
            <Select
              allowClear
              placeholder="Выберите страну"
              options={[
                { value: 'Корея', label: 'Корея' },
                { value: 'Китай', label: 'Китай' },
              ]}
            />
          </Form.Item>
          <Form.Item name="city" label="Город">
            <Input placeholder="Москва" />
          </Form.Item>
          <Form.Item name="timing" label="Сроки">
            <Input placeholder="1-2 месяца" />
          </Form.Item>
          <Form.Item name="summary" label="Описание / транскрипт">
            <Input.TextArea rows={3} placeholder="Краткое описание обращения" />
          </Form.Item>
          <Form.Item name="distribution_mode" label="Режим дистрибуции">
            <Select
              options={[
                { value: 'coverage', label: 'Охват' },
                { value: 'speed', label: 'Скорость' },
                { value: 'exclusive', label: 'Эксклюзив' },
              ]}
            />
          </Form.Item>
          <Form.Item name="is_test" label="Тестовый лид" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
