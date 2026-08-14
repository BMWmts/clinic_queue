"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { authApi } from "@/lib/api";
import { Alert, Button, Field, TextInput } from "@/components/ui";

/**
 * ฟอร์มเข้าสู่ระบบ
 *
 * ส่งอีเมล/รหัสผ่านไปยัง route handler ของ Next (ไม่ได้ยิงตรงไป Django)
 * เพื่อให้ token ถูกเก็บเป็น httpOnly cookie ตั้งแต่ต้น
 */
export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await authApi.login(email, password);
      router.replace(searchParams.get("next") ?? "/queue");
      router.refresh();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "เข้าสู่ระบบไม่สำเร็จ");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      {errorMessage && <Alert>{errorMessage}</Alert>}

      <Field label="อีเมล">
        <TextInput
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="username"
          required
          placeholder="staff@clinic.test"
        />
      </Field>

      <Field label="รหัสผ่าน">
        <TextInput
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
          minLength={8}
        />
      </Field>

      <Button type="submit" disabled={isSubmitting} className="w-full">
        {isSubmitting ? "กำลังเข้าสู่ระบบ..." : "เข้าสู่ระบบ"}
      </Button>
    </form>
  );
}
