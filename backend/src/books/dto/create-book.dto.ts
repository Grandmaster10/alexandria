import { IsString, IsNotEmpty, MinLength } from 'class-validator';

export class CreateBookDto {
  @IsString()
  @IsNotEmpty()
  title!: string;

  @IsString()
  @IsNotEmpty()
  author!: string;

  @IsString()
  @IsNotEmpty()
  type!: string;

  @IsString()
  @MinLength(10)
  description!: string;
}