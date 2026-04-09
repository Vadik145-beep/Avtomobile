import { useEffect, useState, useCallback } from 'react'
import {
  Table,
  Input,
  Button,
  Drawer,
  Space,
  Typography,
  Statistic,
  Row,
  Col,
  Card,
  Form,
  InputNumber,
  Tag,
  Spin,
  Alert,
  App,
  Divider,
  Tabs,
} from 'antd'
import type { TableColumnsType } from 'antd'
import {
  SearchOutlined,
  GiftOutlined,
  ReloadOutlined,
  MinusCircleOutlined,
  PlayCircleOutlined,
  StopOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import client from '../api/client'

const { Text } = Typography

interface User {
  telegram_id: number
  username: string | null
  limit_count: number
  icebreaker_active: boolean
  created_at: string
}

interface Transaction {
  id: number
  type: 'purchase' | 'debit' | 'bonus'
  amount: number
  comment: string | null
  source: string | null
  created_at: string
}

const txTypeLabel: Record<string, { label: string; color: string }> = {
  purchase: { label: 'Покупка', color: 'blue' },
  debit: { label: 'Списание', color: 'red' },
  bonus: { label: 'Бонус', color: 'green' },
}

export default function Users() {
  const { message } = App.useApp()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchId, setSearchId] = useState('')
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 20

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [txLoading, setTxLoading] = useState(false)
  const [bonusLoading, setBonusLoading] = useState(false)
  const [bonusForm] = Form.useForm()
  const [deductLoading, setDeductLoading] = useState(false)
  const [deductForm] = Form.useForm()
  const [icebreakerLoadingId, setIcebreakerLoadingId] = useState<number | null>(null)

  const loadUsers = useCallback(async (p = page, sid = searchId) => {
    setLoading(true)
    setError(null)
    try {
      if (sid.trim()) {
        const res = await client.get(`/users/${sid.trim()}`)
        setUsers([res.data])
        setTotal(1)
      } else {
        const res = await client.get('/users', {
          params: { skip: (p - 1) * pageSize, limit: pageSize },
        })
        setUsers(Array.isArray(res.data) ? res.data : res.data.items ?? [])
        setTotal(res.data.total ?? res.data.length ?? 0)
      }
    } catch {
      setError('Не удалось загрузить пользователей')
    } finally {
      setLoading(false)
    }
  }, [page, searchId])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  const openDrawer = async (user: User) => {
    setSelectedUser(user)
    setDrawerOpen(true)
    setTxLoading(true)
    try {
      const res = await client.get(`/users/${user.telegram_id}/transactions`)
      setTransactions(Array.isArray(res.data) ? res.data : res.data.items ?? [])
    } catch {
      setTransactions([])
    } finally {
      setTxLoading(false)
    }
  }

  const handleBonus = async (values: { amount: number; comment: string }) => {
    if (!selectedUser) return
    setBonusLoading(true)
    try {
      await client.post(`/users/${selectedUser.telegram_id}/bonus`, values)
      message.success(`Начислено ${values.amount} лимитов`)
      bonusForm.resetFields()
      setSelectedUser((prev) => prev ? { ...prev, limit_count: prev.limit_count + values.amount } : prev)
      setUsers((prev) =>
        prev.map((u) =>
          u.telegram_id === selectedUser.telegram_id
            ? { ...u, limit_count: u.limit_count + values.amount }
            : u
        )
      )
      const res = await client.get(`/users/${selectedUser.telegram_id}/transactions`)
      setTransactions(Array.isArray(res.data) ? res.data : res.data.items ?? [])
    } catch {
      message.error('Ошибка начисления бонуса')
    } finally {
      setBonusLoading(false)
    }
  }

  const handleDeduct = async (values: { amount: number; comment: string }) => {
    if (!selectedUser) return
    setDeductLoading(true)
    try {
      await client.post(`/users/${selectedUser.telegram_id}/deduct`, values)
      message.success(`Снято ${values.amount} лимитов`)
      deductForm.resetFields()
      setSelectedUser((prev) => prev ? { ...prev, limit_count: prev.limit_count - values.amount } : prev)
      setUsers((prev) =>
        prev.map((u) =>
          u.telegram_id === selectedUser.telegram_id
            ? { ...u, limit_count: u.limit_count - values.amount }
            : u
        )
      )
      const res = await client.get(`/users/${selectedUser.telegram_id}/transactions`)
      setTransactions(Array.isArray(res.data) ? res.data : res.data.items ?? [])
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      message.error(detail ?? 'Ошибка списания лимитов')
    } finally {
      setDeductLoading(false)
    }
  }

  const handleToggleIcebreaker = async (user: User, e: React.MouseEvent) => {
    e.stopPropagation()
    setIcebreakerLoadingId(user.telegram_id)
    const newActive = !user.icebreaker_active
    try {
      const res = await client.post(`/users/${user.telegram_id}/icebreaker`, { active: newActive })
      const updated: User = res.data
      setUsers((prev) =>
        prev.map((u) => u.telegram_id === user.telegram_id ? { ...u, icebreaker_active: updated.icebreaker_active } : u)
      )
      if (selectedUser?.telegram_id === user.telegram_id) {
        setSelectedUser((prev) => prev ? { ...prev, icebreaker_active: updated.icebreaker_active } : prev)
      }
      message.success(newActive ? 'Ледокол запущен' : 'Ледокол остановлен')
    } catch {
      message.error('Не удалось изменить статус ледокола')
    } finally {
      setIcebreakerLoadingId(null)
    }
  }

  const columns: TableColumnsType<User> = [
    {
      title: 'Telegram ID',
      dataIndex: 'telegram_id',
      width: 130,
      render: (v) => <Text code>{v}</Text>,
    },
    {
      title: 'Username',
      dataIndex: 'username',
      render: (v) => v ? `@${v}` : <Text type="secondary">—</Text>,
    },
    {
      title: 'Лимит',
      dataIndex: 'limit_count',
      width: 100,
      render: (v) => (
        <Tag color={v > 0 ? 'green' : 'red'}>{v}</Tag>
      ),
      sorter: (a, b) => a.limit_count - b.limit_count,
    },
    {
      title: 'Ледокол',
      dataIndex: 'icebreaker_active',
      width: 120,
      render: (v, record) => {
        const active = v && record.limit_count > 0
        return <Tag color={active ? 'green' : 'default'}>{active ? 'Активен' : 'Не активен'}</Tag>
      },
      filters: [
        { text: 'Активен', value: true },
        { text: 'Не активен', value: false },
      ],
      onFilter: (value, record) => record.icebreaker_active === value,
    },
    {
      title: 'Зарегистрирован',
      dataIndex: 'created_at',
      width: 170,
      render: (v) => dayjs(v).format('DD.MM.YYYY HH:mm'),
    },
    {
      title: '',
      width: 200,
      render: (_, record) => (
        <Space size={4} onClick={(e) => e.stopPropagation()}>
          {record.icebreaker_active ? (
            <Button
              size="small"
              danger
              icon={<StopOutlined />}
              loading={icebreakerLoadingId === record.telegram_id}
              onClick={(e) => handleToggleIcebreaker(record, e)}
            >
              Остановить
            </Button>
          ) : (
            <Button
              size="small"
              type="primary"
              icon={<PlayCircleOutlined />}
              loading={icebreakerLoadingId === record.telegram_id}
              onClick={(e) => handleToggleIcebreaker(record, e)}
            >
              Запустить
            </Button>
          )}
          <Button size="small" onClick={() => openDrawer(record)}>
            Подробнее
          </Button>
        </Space>
      ),
    },
  ]

  const txColumns: TableColumnsType<Transaction> = [
    {
      title: 'Дата',
      dataIndex: 'created_at',
      width: 150,
      render: (v) => dayjs(v).format('DD.MM.YY HH:mm'),
    },
    {
      title: 'Тип',
      dataIndex: 'type',
      width: 100,
      render: (v: string) => {
        const t = txTypeLabel[v] ?? { label: v, color: 'default' }
        return <Tag color={t.color}>{t.label}</Tag>
      },
    },
    {
      title: 'Кол-во',
      dataIndex: 'amount',
      width: 80,
      render: (v, r) => (
        <Text style={{ color: r.type === 'debit' ? '#ff4d4f' : '#52c41a' }}>
          {r.type === 'debit' ? `-${v}` : `+${v}`}
        </Text>
      ),
    },
    {
      title: 'Комментарий',
      dataIndex: 'comment',
      render: (v) => v ?? <Text type="secondary">—</Text>,
    },
  ]

  return (
    <>
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Row gutter={12} align="middle">
          <Col flex="auto">
            <Input
              placeholder="Поиск по Telegram ID"
              prefix={<SearchOutlined />}
              value={searchId}
              onChange={(e) => setSearchId(e.target.value)}
              onPressEnter={() => { setPage(1); loadUsers(1, searchId) }}
              allowClear
              onClear={() => { setSearchId(''); setPage(1); loadUsers(1, '') }}
              style={{ maxWidth: 320 }}
            />
          </Col>
          <Col>
            <Button icon={<SearchOutlined />} onClick={() => { setPage(1); loadUsers(1, searchId) }} type="primary">
              Найти
            </Button>
          </Col>
          <Col>
            <Button icon={<ReloadOutlined />} onClick={() => { setSearchId(''); setPage(1); loadUsers(1, '') }}>
              Сбросить
            </Button>
          </Col>
        </Row>

        {error && <Alert type="error" message={error} />}

        <Table
          dataSource={users}
          columns={columns}
          rowKey="telegram_id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: false,
            onChange: (p) => { setPage(p); loadUsers(p) },
          }}
          onRow={(record) => ({ onClick: () => openDrawer(record), style: { cursor: 'pointer' } })}
        />
      </Space>

      <Drawer
        title={
          selectedUser ? (
            <Space>
              <Text strong>Пользователь</Text>
              <Text code>{selectedUser.telegram_id}</Text>
              {selectedUser.username && <Text type="secondary">@{selectedUser.username}</Text>}
              <Tag color={selectedUser.icebreaker_active ? 'green' : 'default'}>
                {selectedUser.icebreaker_active ? '🚀 Ледокол активен' : '🛑 Ледокол выключен'}
              </Tag>
            </Space>
          ) : null
        }
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); bonusForm.resetFields(); deductForm.resetFields() }}
        width={520}
        extra={
          selectedUser && (
            <Row gutter={16}>
              <Col>
                <Statistic title="Лимит" value={selectedUser.limit_count} valueStyle={{ fontSize: 18 }} />
              </Col>
            </Row>
          )
        }
      >
        {selectedUser && (
          <>
            <Card size="small" style={{ marginBottom: 16 }}>
              <Tabs
                defaultActiveKey="bonus"
                items={[
                  {
                    key: 'bonus',
                    label: <><GiftOutlined /> Начислить</>,
                    children: (
                      <Form form={bonusForm} layout="inline" onFinish={handleBonus}>
                        <Form.Item
                          name="amount"
                          rules={[{ required: true, message: 'Укажите кол-во' }]}
                        >
                          <InputNumber min={1} max={10000} placeholder="Кол-во" style={{ width: 110 }} />
                        </Form.Item>
                        <Form.Item
                          name="comment"
                          rules={[{ required: true, message: 'Введите комментарий' }]}
                          style={{ flex: 1 }}
                        >
                          <Input placeholder="Комментарий (обязательно)" />
                        </Form.Item>
                        <Form.Item>
                          <Button type="primary" htmlType="submit" loading={bonusLoading}>
                            Начислить
                          </Button>
                        </Form.Item>
                      </Form>
                    ),
                  },
                  {
                    key: 'deduct',
                    label: <><MinusCircleOutlined /> Снять</>,
                    children: (
                      <Form form={deductForm} layout="inline" onFinish={handleDeduct}>
                        <Form.Item
                          name="amount"
                          rules={[{ required: true, message: 'Укажите кол-во' }]}
                        >
                          <InputNumber min={1} max={10000} placeholder="Кол-во" style={{ width: 110 }} />
                        </Form.Item>
                        <Form.Item
                          name="comment"
                          rules={[{ required: true, message: 'Введите комментарий' }]}
                          style={{ flex: 1 }}
                        >
                          <Input placeholder="Комментарий (обязательно)" />
                        </Form.Item>
                        <Form.Item>
                          <Button danger htmlType="submit" loading={deductLoading}>
                            Снять
                          </Button>
                        </Form.Item>
                      </Form>
                    ),
                  },
                ]}
              />
            </Card>

            <Divider orientation="left">История транзакций</Divider>

            {txLoading ? (
              <Spin />
            ) : (
              <Table
                dataSource={transactions}
                columns={txColumns}
                rowKey="id"
                size="small"
                pagination={{ pageSize: 15, showSizeChanger: false }}
                locale={{ emptyText: 'Транзакций нет' }}
              />
            )}
          </>
        )}
      </Drawer>
    </>
  )
}
