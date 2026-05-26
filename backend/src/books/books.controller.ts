import { Controller, Get, Post, Body, Param } from '@nestjs/common';
import { BooksService } from './books.service';
import { CreateBookDto } from './dto/create-book.dto';

@Controller('books')
export class BooksController {
  constructor(private readonly booksService: BooksService) {}

  @Post()
  createBook(@Body() createBookDto: CreateBookDto) {
    return this.booksService.createBook(createBookDto);
  }

  @Post('search/text')
  async searchByText(@Body() body: { query: string }) {
    if (!body.query) {
      return { message: "Query text is required." };
    }
    return this.booksService.searchByText(body.query);
  }

  @Get()
  findAll() {
    return this.booksService.findAll();
  }

  @Get(':id/recommendations')
  getRecommendations(@Param('id') id: string) {
    return this.booksService.getRecommendations(id);
  }
}
