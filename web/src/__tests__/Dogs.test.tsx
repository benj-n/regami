import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import Dogs from '../pages/Dogs'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'
import { ToastProvider } from '../context/ToastContext'
import * as apiMod from '../services/api'

// Mock API functions used by Dogs page
vi.mock('../services/api', () => ({
  apiGet: vi.fn().mockImplementation((url: string) => {
    if (url === '/dogs/me') {
      return Promise.resolve([])
    }
    if (url === '/users/me') {
      return Promise.resolve({ location_lat: null, location_lng: null })
    }
    return Promise.resolve([])
  }),
  apiPost: vi.fn().mockImplementation((_p: string, body: any) => Promise.resolve({ id: 1, name: body.name, birth_month: body.birth_month || 1, birth_year: body.birth_year || 2023, sex: body.sex || 'male', age_years: 2, created_at: new Date().toISOString() })),
  apiPut: vi.fn().mockImplementation((_p: string, body: any) => Promise.resolve({ id: 1, name: body.name, birth_month: 1, birth_year: 2023, sex: 'male', age_years: 2, created_at: new Date().toISOString() })),
  apiDeleteVoid: vi.fn().mockResolvedValue(undefined),
  apiPostVoid: vi.fn().mockResolvedValue(undefined),
  apiUpload: vi.fn().mockImplementation((_p: string, _fd: FormData) => Promise.resolve({ id: 1, name: 'DOG21', photo_url: '/static/uploads/img.png', birth_month: 1, birth_year: 2023, sex: 'male', age_years: 2, created_at: new Date().toISOString() })),
}))

function Providers({ children }: { children: React.ReactNode }) {
  // Prime token so Dogs page functions (which guard on token) can execute
  if (typeof window !== 'undefined') {
    window.localStorage.setItem('token', 'test-token')
  }
  return (
    <ToastProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={["/dogs"]}>{children}</MemoryRouter>
      </AuthProvider>
    </ToastProvider>
  )
}

describe('Dogs page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('creates a dog with valid name', async () => {
    await act(async () => {
      render(
        <Providers>
          <Dogs />
        </Providers>
      )
    })

    // Wait for loading to complete - look for "Créer un chien" heading
    await screen.findByText('Créer un chien')

    // Find the create form input by its label text pattern
    const nameInput = screen.getByLabelText(/Nom \(ex:/i) as HTMLInputElement
    fireEvent.change(nameInput, { target: { value: 'DOG21' } })

    const createBtn = screen.getByText('Créer')
    await act(async () => {
      fireEvent.click(createBtn)
    })

    await waitFor(() => expect(screen.getByText(/Chien créé/)).toBeInTheDocument())
  })

  it('uploads a photo with mock File and updates list', async () => {
    await act(async () => {
      render(
        <Providers>
          <Dogs />
        </Providers>
      )
    })

    // Wait for loading to complete
    await screen.findByText('Créer un chien')

    // Create initial dog
    const nameInput = screen.getByLabelText(/Nom \(ex:/i) as HTMLInputElement
    fireEvent.change(nameInput, { target: { value: 'DOG21' } })
    await act(async () => {
      fireEvent.click(screen.getByText('Créer'))
    })
    await waitFor(() => expect(screen.getByText(/Chien créé/)).toBeInTheDocument())

    // Find file input and upload a mock file
    const fileInputs = screen.getAllByLabelText(/Photo:/)
    const fileInput = fileInputs[0] as HTMLInputElement
    const file = new File([new Uint8Array([0x89, 0x50, 0x4e, 0x47])], 'photo.png', { type: 'image/png' })
    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [file] } })
    })
    await waitFor(() => expect(screen.getByText(/Photo mise à jour/)).toBeInTheDocument())
  })

  it('adds and removes a co-owner by user id', async () => {
    await act(async () => {
      render(
        <Providers>
          <Dogs />
        </Providers>
      )
    })

    // Wait for loading to complete
    await screen.findByText('Créer un chien')

    // Create a dog first
    const nameInput = screen.getByLabelText(/Nom \(ex:/i) as HTMLInputElement
    fireEvent.change(nameInput, { target: { value: 'DOG21' } })
    await act(async () => {
      fireEvent.click(screen.getByText('Créer'))
    })
    await waitFor(() => expect(screen.getByText(/Chien créé/)).toBeInTheDocument())

    const uidInput = screen.getByLabelText('ID co-propriétaire') as HTMLInputElement
    fireEvent.change(uidInput, { target: { value: '12345678' } })

    await act(async () => {
      fireEvent.click(screen.getByText('Ajouter co-propriétaire'))
    })
    await waitFor(() => expect(screen.getByText(/Co-propriétaire ajouté/)).toBeInTheDocument())
    expect((apiMod.apiPostVoid as any)).toHaveBeenCalled()

    // Remove
    fireEvent.change(uidInput, { target: { value: '12345678' } })
    await act(async () => {
      fireEvent.click(screen.getByText('Retirer co-propriétaire'))
    })
    await waitFor(() => expect(screen.getByText(/Co-propriétaire retiré/)).toBeInTheDocument())
    expect((apiMod.apiDeleteVoid as any)).toHaveBeenCalled()
  })

  it('rejects non-image uploads client-side and does not call apiUpload', async () => {
    await act(async () => {
      render(
        <Providers>
          <Dogs />
        </Providers>
      )
    })

    // Wait for loading to complete
    await screen.findByText('Créer un chien')

    // Create a dog first
    const nameInput = screen.getByLabelText(/Nom \(ex:/i) as HTMLInputElement
    fireEvent.change(nameInput, { target: { value: 'DOG21' } })
    await act(async () => {
      fireEvent.click(screen.getByText('Créer'))
    })
    await waitFor(() => expect(screen.getByText(/Chien créé/)).toBeInTheDocument())

    const fileInputs = screen.getAllByLabelText(/Photo:/)
    const fileInput = fileInputs[0] as HTMLInputElement
    const badFile = new File([new Uint8Array([0x00, 0x01])], 'note.txt', { type: 'text/plain' })
    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [badFile] } })
    })

    await waitFor(() => expect(screen.getByText(/Fichier image requis/)).toBeInTheDocument())
    expect((apiMod.apiUpload as any)).not.toHaveBeenCalled()
  })
})
