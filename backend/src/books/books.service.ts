import { Injectable, InternalServerErrorException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { CreateBookDto } from './dto/create-book.dto';
import { Book } from '@prisma/client';
import axios from 'axios';

@Injectable()
export class BooksService {
  constructor(
    private prisma: PrismaService,
    private httpService: HttpService, 
  ) {}

  async createBook(createBookDto: CreateBookDto) {
    const { title, author, type, description } = createBookDto;

    try {
      const pythonResponse = await firstValueFrom(
        this.httpService.post('http://localhost:8000/embed', { text: description })
      );
      const embeddingVector = pythonResponse.data; 

      const vectorString = `[${embeddingVector.join(',')}]`;

      const result = await this.prisma.$queryRaw<Book[]>`
        INSERT INTO "Book" (id, title, author, type, description, embedding, "updatedAt")
        VALUES (
          gen_random_uuid(), 
          ${title}, 
          ${author}, 
          ${type}, 
          ${description}, 
          ${vectorString}::vector, 
          now()
        )
        RETURNING *;
      `;
      return result[0];
    } catch (error) {
      throw new InternalServerErrorException('Failed to process book and embedding.');
    }
  }

  async getRecommendations(bookId: string, limit: number = 5) {
    const recommendations = await this.prisma.$queryRaw`
      SELECT 
        id, title, author, description,
        1 - (embedding <-> (SELECT embedding FROM "Book" WHERE id = ${bookId})) as similarity_score
      FROM "Book"
      WHERE id != ${bookId}
      ORDER BY embedding <-> (SELECT embedding FROM "Book" WHERE id = ${bookId})
      LIMIT ${limit};
    `;
    return recommendations;
  }

  async searchByText(query: string) {
    try {
      const mlResponse = await axios.post('http://localhost:8000/embed', {
        text: query
      });

      const embedding = mlResponse.data;
      const vectorString = `[${embedding.join(',')}]`;

      const recommendations = await this.prisma.$queryRaw`
        SELECT 
          id, 
          title, 
          author,
          type, 
          description, 
          (1 - (embedding <=> ${vectorString}::vector))::float AS similarity
        FROM "Book"
        ORDER BY embedding <=> ${vectorString}::vector
        LIMIT 5;
      `;

      return recommendations;

    } catch (error) {
      console.error('Text Search Error:', error);
      throw new Error('Failed to process semantic search.');
    }
  }

  async findAll() {
    return this.prisma.book.findMany({
      select: { id: true, title: true, author: true, type: true, description: true }
    });
  }
}