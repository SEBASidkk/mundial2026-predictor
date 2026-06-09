import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NavbarComponent } from './navbar.component';
import { RouterTestingModule } from '@angular/router/testing';

describe('NavbarComponent', () => {
  let fixture: ComponentFixture<NavbarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NavbarComponent, RouterTestingModule],
    }).compileComponents();
    fixture = TestBed.createComponent(NavbarComponent);
    fixture.detectChanges();
  });

  it('renders brand name', () => {
    expect(fixture.nativeElement.textContent).toContain('MUNDIAL');
  });

  it('renders Dashboard nav link', () => {
    const links = fixture.nativeElement.querySelectorAll('a');
    const texts = Array.from(links).map((l: any) => l.textContent.trim());
    expect(texts).toContain('Dashboard');
  });
});
