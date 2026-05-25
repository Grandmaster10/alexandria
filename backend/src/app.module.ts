import { Module } from '@nestjs/common';
import { PrismaModule } from './prisma/prisma.module';
import { BooksModule } from './books/books.module';

@Module({
  imports: [PrismaModule, BooksModule],
})
export class AppModule {}
